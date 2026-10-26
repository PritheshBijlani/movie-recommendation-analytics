"""Who Gets Recommended? - a popularity-bias audit you can play with.
Run:  streamlit run app.py        (needs ./artifacts from the notebook export cells)"""
import time
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import core
import style

alt.data_transformers.disable_max_rows()   # the catalog map plots thousands of points

st.set_page_config(page_title="Who gets recommended?", layout="wide", initial_sidebar_state="expanded")
st.markdown(style.CSS, unsafe_allow_html=True)


@st.cache_resource
def get_artifacts():
    here = Path(__file__).parent                      # artifacts/ may sit inside app/ or next to it (repo root)
    return core.load_artifacts(here / "artifacts" if (here / "artifacts").exists() else here.parent / "artifacts")


A = get_artifacts()


@st.cache_resource
def get_map_background(n=2500):
    """The grey dots of the catalog map: a fixed sample of the most-rated titles, built once. Sending all 15,000 points on every click made the app lag."""
    X, it = A["coords"], A["items"]
    keep = it.sort_values("train_count", ascending=False).index[:n]
    return pd.DataFrame({"x": X[keep, 0], "y": X[keep, 1], "title": it.title.to_numpy()[keep], "tier": it.group.to_numpy()[keep]})
meta, items = A["meta"], A["items"]
users = [int(u) for u in A["users"]]
MIN_PICKS, MAX_PICKS = 5, 10
GREASE, FIXER, ACETATE = style.GREASE, style.FIXER, style.ACETATE
html = lambda s: st.markdown(s, unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar
st.sidebar.markdown("### Balance strength")
lam = st.sidebar.select_slider("How hard the balanced list tries to match your genre mix", options=meta["lams"], value=meta["default_lam"], label_visibility="collapsed")
st.sidebar.caption(f"Left: keep the model's own order. Right: rebuild each list to mirror your genre mix, which costs some accuracy. "
                   f"{meta['default_lam']} is the setting used in the feedback-loop simulation.")
st.sidebar.markdown("### Reading the frames")
st.sidebar.markdown(style.strip(items, [int(items[items.group == g].sort_values("train_count", ascending=False).item_idx.iloc[k]) for g, k in (("head", 0), ("mid", 3), ("tail", 3))], cols=3), unsafe_allow_html=True)
st.sidebar.caption("A bright frame is a head title: it already gets most of the attention. Grey is mid. Dark is tail, the long run of titles that rarely get shown. "
                   "Red circles mark your picks, or titles a viewer really liked later.")
st.sidebar.caption("MovieLens ratings, offline replay. Nothing here is a live service.")

html("<div class='masthead'><div><div style='font:700 .72rem DM Sans,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:#c8d9cc;margin-bottom:9px'>RECOMMENDER SYSTEMS · INTERACTIVE AUDIT</div><div class='stamp'>Who gets recommended?</div></div>"
     "<div class='sub'>A hands-on investigation into popularity bias. Build a movie profile, compare recommendation strategies, and see how feedback loops shape what everyone gets to watch.</div></div>")
t_build, t_blind, t_loop, t_audit, t_room = st.tabs(["Build your strip", "Blind test", "Rewind the loop", "Audit a viewer", "Boardroom"])


def catalog_map(picks, std, mit):
    X, it = A["coords"], items
    bg = get_map_background()
    rows = [{"x": X[i, 0], "y": X[i, 1], "title": it.title[i], "who": who} for who, idx in (("your picks", picks), ("standard", std), ("balanced", mit)) for i in idx]
    who_dom = ["your picks", "standard", "balanced"]
    base = alt.Chart(bg).mark_circle(size=16, color="#9aa89d", opacity=0.4).encode(x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None), tooltip=["title", "tier"])
    top = alt.Chart(pd.DataFrame(rows)).mark_point(filled=True, size=150, opacity=0.95, stroke="white", strokeWidth=1).encode(
        x="x:Q", y="y:Q", tooltip=["title", "who"],
        color=alt.Color("who:N", scale=alt.Scale(domain=who_dom, range=[GREASE, ACETATE, FIXER]), legend=alt.Legend(title=None, orient="bottom")),
        shape=alt.Shape("who:N", scale=alt.Scale(domain=who_dom, range=["circle", "square", "diamond"]), legend=None))
    return (base + top).properties(height=380).configure_view(strokeWidth=0).configure(background="transparent")


# ================================================================== 1. Build your strip
with t_build:
    if not A["has_factors"]:
        st.warning("This tab needs artifacts/factors.npz (notebook export cell 29).")
    else:
        eligible = items[items.train_count >= 3].sort_values("train_count", ascending=False).head(4000)   # 4,000 options: a 15k-option dropdown is re-sent to the browser on every click
        title_of = dict(zip(items.item_idx, items.title))

        def preset(genre):
            g = eligible[eligible.genres.str.contains(genre, regex=False)]
            st.session_state["picks"] = g[g.group == "head"].item_idx.tolist()[:2] + g[g.group == "mid"].item_idx.tolist()[:4]

        def preset_niche():
            st.session_state["picks"] = eligible[(eligible.group == "tail") & (eligible.train_count >= 15)].item_idx.tolist()[:6]

        st.markdown(f"#### Pick {MIN_PICKS} to {MAX_PICKS} movies you like. They become your strip.")
        picks = st.multiselect("Search by title", eligible.item_idx.tolist(), key="picks", max_selections=MAX_PICKS, format_func=lambda i: title_of[i],
                               placeholder="Start typing a title")
        cols = st.columns([1, 1, 1, 1, 1.25, 0.7, 2])
        for col, g in zip(cols[:4], ["Sci-Fi", "Romance", "Horror", "Children's"]):
            col.button(f"{g} fan", on_click=preset, args=(g,), use_container_width=True)
        cols[4].button("Niche taste", on_click=preset_niche, use_container_width=True)
        cols[5].button("Clear", on_click=lambda: st.session_state.update(picks=[]), use_container_width=True)
        html(style.strip(items, picks, picks=picks, pad_to=max(MIN_PICKS, len(picks))))

        if len(picks) < MIN_PICKS:
            n = MIN_PICKS - len(picks)
            html(f"<div class='note'>{n} more to go</div>")
        else:
            std, mit, p = core.recommend_for_picks(A, picks, lam)
            std_s, mit_s, pick_s = core.list_share(A, std), core.list_share(A, mit), core.pick_summary(A, picks)
            n_head_std, n_head_mit = round(std_s["head"] * 10), round(mit_s["head"] * 10)
            st.markdown("---")
            st.markdown("#### Standard recommender")
            html(style.strip(items, std, notes=[f"like {t}" for t in core.because_of(A, picks, std)]))
            st.markdown(f"#### Balanced recommender (strength {lam})")
            html(style.strip(items, mit, notes=[f"like {t}" for t in core.because_of(A, picks, mit)]))

            verdict = (f"Your picks are {pick_s['head']:.0%} head, {pick_s['mid']:.0%} mid and {pick_s['tail']:.0%} tail. "
                       f"The standard strip has {n_head_std} head titles out of 10; the balanced strip has {n_head_mit}.")
            pm = A["pop"]; ps, pb = pm[pm.setting == "standard"].iloc[0], core.population_row(A, lam)[1]
            verdict += (f" Across all {meta['n_users']:,} test viewers, the balanced pipeline gives {pb['tail_%']:.1f}% of its slots to tail titles "
                        f"and the standard one {ps['tail_%']:.2f}%.")
            html(f"<div class='verdict'>{verdict}</div>")
            st.markdown("##### How much of each strip is blockbuster")
            html(style.exposure_bar("Your picks", pick_s) + style.exposure_bar("Standard", std_s) + style.exposure_bar("Balanced", mit_s, True)
                 + style.exposure_bar("What viewers liked next", A["demand"]))
            st.caption("Bright = head, grey = mid, dark = tail. The last bar is what MovieLens viewers really went on to like in the held-out window.")

            m_std, m_mit = core.list_stats(A, std, p), core.list_stats(A, mit, p)
            html(style.readouts([
                ("Tail titles in the strip", str(m_mit["tail"]), f"{m_mit['tail'] - m_std['tail']:+d} vs standard", False),
                ("More popular than", f"{m_mit['avg_pop_pct']:.0%} of titles", f"{(m_mit['avg_pop_pct'] - m_std['avg_pop_pct']) * 100:+.0f} pts vs standard", False),
                ("Genre variety", f"{m_mit['ILD']:.2f}", f"{m_mit['ILD'] - m_std['ILD']:+.2f} vs standard", False),
                ("Distance from your genre mix", f"{m_mit['genre_mismatch']:.2f}", f"{m_mit['genre_mismatch'] - m_std['genre_mismatch']:+.2f} vs standard (lower is closer)", False)]))
            with st.expander("Show the catalog map"):
                st.altair_chart(catalog_map(picks, std, mit), use_container_width=True)
                st.caption("Each grey dot is a title; titles liked by similar people sit near each other. Hover for names.")
            st.caption("A handful of picks gives a rough profile, so treat this as a demo, not a verdict. The balanced list is not always less head-heavy: "
                       "it matches your genre mix and de-emphasises blockbusters only through how it was trained.")


# ================================================================== 2. Blind test
with t_blind:
    st.markdown("#### Which list would you send this viewer?")
    st.caption("A real MovieLens viewer, two lists, labels hidden. Choose first, then see which recommender wrote which and what the viewer actually went on to like.")
    bt = st.session_state.setdefault("bt", {"round": None, "votes": []})

    def deal():
        rng = np.random.default_rng()
        r = core.random_viewer(A, rng, lam, n_sample=5)
        r["a_is_std"] = bool(rng.integers(2)); r["choice"] = None
        bt["round"] = r

    def vote(which):
        bt["round"]["choice"] = which
        r = bt["round"]; a_list, b_list = (r["std"], r["mit"]) if r["a_is_std"] else (r["mit"], r["std"])
        hits = lambda L: sum(int(i) in r["future"] for i in L)
        bt["votes"].append({"chose_balanced": (which == "A") != r["a_is_std"], "hits_a": hits(a_list), "hits_b": hits(b_list), "a_is_std": r["a_is_std"]})

    if bt["round"] is None:
        html("<div class='note'>Deal a viewer to start</div>")
        st.button("Deal a viewer", on_click=deal, key="deal0")
    else:
        r = bt["round"]; a_list, b_list = (r["std"], r["mit"]) if r["a_is_std"] else (r["mit"], r["std"])
        st.markdown("**This viewer liked**")
        html(style.strip(items, r["profile"]["sample_idx"]))
        reveal = r["choice"] is not None
        hit_set = r["future"] if reveal else ()
        st.markdown("**List A**" + (f" - {'standard' if r['a_is_std'] else 'balanced'}" if reveal else ""))
        html(style.strip(items, a_list, hits=hit_set))
        st.markdown("**List B**" + (f" - {'standard' if not r['a_is_std'] else 'balanced'}" if reveal else ""))
        html(style.strip(items, b_list, hits=hit_set))
        if not reveal:
            c1, c2, _ = st.columns([1, 1, 4])
            c1.button("Send list A", on_click=vote, args=("A",), key="voteA", use_container_width=True)
            c2.button("Send list B", on_click=vote, args=("B",), key="voteB", use_container_width=True)
        else:
            v = bt["votes"][-1]
            html(f"<div class='verdict'>Red circles are titles this viewer really liked later: list A hit {v['hits_a']}, list B hit {v['hits_b']}. "
                 f"One viewer is a coin flip; the pattern shows over many rounds.</div>")
            st.button("Deal another viewer", on_click=deal, key="deal1")
    if bt["votes"]:
        n = len(bt["votes"]); k = sum(v["chose_balanced"] for v in bt["votes"])
        better = sum((v["hits_a"] > v["hits_b"]) == (not v["a_is_std"]) and v["hits_a"] != v["hits_b"] for v in bt["votes"])
        st.caption(f"Your tally: you chose the balanced list in {k} of {n} rounds. The balanced list had more hits in {better} of them.")


# ================================================================== 3. Rewind the loop
with t_loop:
    L, R = A["loop"], (A["biz"] or {}).get("rounds", 24)
    if L is None:
        st.warning("This tab needs artifacts/loop.csv (notebook export cell 30).")
    else:
        st.markdown("#### What happens when a recommender learns from its own clicks")
        st.caption(f"Assumption-based simulation: {A['biz']['n_sim_users']:,} simulated viewers, {R} rounds. Everything they watch comes from the recommendations, "
                   f"and the model retrains every {A['biz']['retrain_every']} rounds on what they clicked. A third run never retrains, to separate the loop from simply running out of titles.")
        ARM = {"Baseline ALS": "Standard, learns from clicks", "Mitigated": "Balanced, learns from clicks", "Baseline, never retrained (control)": "Standard, frozen"}
        L = L.assign(arm=L.arm.map(ARM)); order = list(ARM.values())
        METRIC = {"Titles shown at least once (%)": "coverage_cum_%", "How wide attention spreads (effective titles)": "effective_titles", "Slots going to head titles (%)": "head_slots_%"}
        which = st.radio("Measure", list(METRIC), horizontal=True, label_visibility="collapsed")
        col_m = METRIC[which]
        top, play_col = st.columns([4, 1])
        t = top.slider("Round", 1, R, R, key="round_slider")
        slot = st.empty()

        def draw(t):
            with slot.container():
                d = L[L["round"] <= t]
                lines = alt.Chart(d).mark_line(strokeWidth=3).encode(
                    x=alt.X("round:Q", title="Round", scale=alt.Scale(domain=[1, R])), y=alt.Y(f"{col_m}:Q", title=which, scale=alt.Scale(zero=False)),
                    color=alt.Color("arm:N", scale=alt.Scale(domain=order, range=[ACETATE, FIXER, "#8f9ca2"]), legend=alt.Legend(title=None, orient="bottom")),
                    strokeDash=alt.StrokeDash("arm:N", scale=alt.Scale(domain=order, range=[[1, 0], [1, 0], [6, 4]]), legend=None))
                rule = alt.Chart(pd.DataFrame({"round": [t]})).mark_rule(color=GREASE, strokeWidth=2).encode(x="round:Q")
                st.altair_chart((lines + rule).properties(height=330).configure(background="transparent").configure_view(strokeWidth=0), use_container_width=True)
                now = L[L["round"] == t].set_index("arm")
                html(style.readouts([(a, f"{now.loc[a, col_m]:.1f}" if col_m != "effective_titles" else f"{now.loc[a, col_m]:.0f}", "", False) for a in order]))

        draw(t)
        if play_col.button("Play from round 1", use_container_width=True):
            for rr in range(1, R + 1):
                draw(rr); time.sleep(0.22)
        st.caption("Read the dashed line as the baseline of what is possible without the loop. The gap between the dark line and the dashed one is the loop's effect.")


# ================================================================== 4. Audit a viewer
with t_audit:
    if "uid" not in st.session_state:
        st.session_state["uid"] = users[0]
    c_a, c_b = st.columns([3, 1])
    if c_b.button("Random viewer", use_container_width=True):
        st.session_state["uid"] = int(np.random.choice(users))
    uid = c_a.selectbox("MovieLens viewer ID", users, index=users.index(st.session_state["uid"]))
    st.session_state["uid"] = uid
    std, mit = core.user_lists(A, uid, lam)
    prof = core.user_profile(A, uid, n_titles=5)
    m_std, m_mit = core.list_metrics(A, uid, std), core.list_metrics(A, uid, mit)
    future = set(A["future"][A["user_pos"][uid]].indices.tolist())
    st.markdown(f"**Viewer {uid}** liked {prof['n_liked']} titles before the cut-off and {prof['n_future']} after it. A sample of what they liked:")
    html(style.strip(items, prof["sample_idx"]))
    st.markdown("#### Standard recommender")
    html(style.strip(items, std, hits=future))
    st.markdown(f"#### Balanced recommender (strength {lam})")
    html(style.strip(items, mit, hits=future))
    st.caption("Red circle = the viewer really liked this title later. One viewer is noisy; the numbers for everyone are below.")
    html(style.readouts([
        ("Hits (of 10)", str(m_mit["hits"]), f"{m_mit['hits'] - m_std['hits']:+d} vs standard", m_mit["hits"] < m_std["hits"]),
        ("Tail titles", str(m_mit["tail"]), f"{m_mit['tail'] - m_std['tail']:+d} vs standard", False),
        ("Genre variety", f"{m_mit['ILD']:.2f}", f"{m_mit['ILD'] - m_std['ILD']:+.2f} vs standard", False),
        ("Distance from own genre mix", f"{m_mit['genre_mismatch']:.2f}", f"{m_mit['genre_mismatch'] - m_std['genre_mismatch']:+.2f} (lower is closer)", False)]))

    st.markdown(f"#### Everyone: what balancing costs and buys at strength {lam}")
    base, cur = core.population_row(A, lam)
    html(style.readouts([
        ("Accuracy kept", f"{cur['rel_NDCG_%']:.1f}%", f"{cur['rel_NDCG_%'] - 100:+.1f} pts", cur["rel_NDCG_%"] < 98),
        ("Slots on tail titles", f"{cur['tail_%']:.2f}%", f"{cur['tail_%'] - base['tail_%']:+.2f} pts", False),
        ("Catalog ever shown", f"{cur['coverage_%']:.1f}%", f"{cur['coverage_%'] - base['coverage_%']:+.1f} pts", False),
        ("Effective titles", f"{cur['effective_titles']:.0f}", f"{cur['effective_titles'] - base['effective_titles']:+.0f}", False)]))
    curve = A["pop"][A["pop"].setting == "mitigated"][["lam", "rel_NDCG_%", "effective_titles"]].rename(columns={"rel_NDCG_%": "Accuracy kept (%)", "effective_titles": "Effective titles"})
    ln = alt.Chart(curve).mark_line(color=FIXER, strokeWidth=3).encode(x=alt.X("Accuracy kept (%):Q", scale=alt.Scale(zero=False)), y=alt.Y("Effective titles:Q", scale=alt.Scale(zero=False)))
    pt = alt.Chart(curve).mark_circle(color=FIXER, size=55).encode(x="Accuracy kept (%):Q", y="Effective titles:Q", tooltip=["lam", "Accuracy kept (%)", "Effective titles"])
    now = alt.Chart(pd.DataFrame({"Accuracy kept (%)": [cur["rel_NDCG_%"]], "Effective titles": [cur["effective_titles"]]})).mark_circle(color=GREASE, size=230).encode(x="Accuracy kept (%):Q", y="Effective titles:Q")
    std_pt = alt.Chart(pd.DataFrame({"Accuracy kept (%)": [100.0], "Effective titles": [base["effective_titles"]]})).mark_point(color=ACETATE, size=170, shape="diamond", filled=True).encode(x="Accuracy kept (%):Q", y="Effective titles:Q")
    st.altair_chart((ln + pt + std_pt + now).properties(height=300).configure(background="transparent").configure_view(strokeWidth=0), use_container_width=True)
    st.caption("Blue = balanced pipeline at each strength. Red = where the slider is now. Black diamond = the standard recommender.")


# ================================================================== 5. Boardroom
with t_room:
    B = A["biz"]
    if B is None:
        st.warning("This tab needs artifacts/business.json (notebook export cell 30).")
    else:
        st.markdown("#### Would a business want this?")
        st.caption("Assumption-based simulation. The simulation supplies three numbers (catalog shown, spread of attention, engagement). Everything else here is a guess you can change. "
                   "It is an illustration, not a forecast.")
        sim = B["sim"]
        html(style.readouts([("Titles ever shown", f"{sim['cov_base']:.0f}% to {sim['cov_mit']:.0f}%", "", False),
                             ("Spread of attention", f"{sim['eff_pct']:+.0f}%", "", False), ("Engagement (clicks)", f"{sim['click_pct']:+.1f}%", "", True)]))
        ASM = {r["key"]: r for r in B["assume"]}
        SC = {"Pessimistic": {"util_recovery": 0.0, "eng_churn_per_pct": 0.10, "div_churn_per_10pct": 0.0}, "Base": {},
              "Optimistic": {"util_recovery": 0.10, "eng_churn_per_pct": 0.02, "div_churn_per_10pct": 0.08}}

        SPEC = [("subs", "Subscribers", 100_000, 10_000_000, 100_000), ("arpu", "Revenue per subscriber per month ($)", 4.0, 30.0, 0.5),
                ("margin", "Profit margin on a retained subscriber-year", 0.05, 0.7, 0.01), ("licensed_share", "Share of catalog that is licensed", 0.0, 1.0, 0.05),
                ("license_cost", "Licence cost per title per year ($)", 1000, 60000, 1000), ("util_recovery", "Share of licence cost put to work when a title gets shown", 0.0, 0.2, 0.01),
                ("eng_churn_per_pct", "Retention lost (pp/yr) per 1% drop in engagement", 0.0, 0.3, 0.01), ("div_churn_per_10pct", "Retention gained (pp/yr) per +10% spread of attention", 0.0, 0.2, 0.01)]
        cast = {k: (int if isinstance(step, int) else float) for k, _, _, _, step in SPEC}      # slider values must match the slider's number type

        def scenario(name):
            for k, r in ASM.items():
                st.session_state[f"as_{k}"] = cast[k](SC[name].get(k, r["base"]))

        sc = st.columns([1, 1, 1, 4])
        for col, nm in zip(sc[:3], SC):
            col.button(nm, on_click=scenario, args=(nm,), use_container_width=True, key=f"sc_{nm}")
        vals = {}
        cl, cr = st.columns(2)
        for n, (k, label, lo, hi, step) in enumerate(SPEC):
            base_v = ASM[k]["base"]; key = f"as_{k}"
            if key not in st.session_state: st.session_state[key] = cast[k](base_v)
            vals[k] = (cl if n % 2 == 0 else cr).slider(label, lo, hi, key=key, step=step)
        res = core.business_case(B, **vals)
        sign = "gain" if res["net"] >= 0 else "loss"
        html(f"<div class='verdict'>Under these assumptions, switching is a net {sign} of {core.money(abs(res['net']))} a year "
             f"({res['net_pct_revenue']:+.2f}% of revenue). Without the licence effect, it breaks even if each +10% in spread of attention keeps "
             f"{res['breakeven_excl_licence']:.3f} points more subscribers a year.</div>")
        comp = pd.DataFrame({"part": ["Engagement drop", "Retention from wider exposure", "Licence value put to work"], "value": [res["engagement"], res["retention"], res["licence"]]})
        bars = alt.Chart(comp).mark_bar(size=26).encode(y=alt.Y("part:N", sort=None, title=None), x=alt.X("value:Q", title="Dollars per year"),
                                                      color=alt.condition(alt.datum.value >= 0, alt.value(FIXER), alt.value(GREASE)), tooltip=["part", alt.Tooltip("value:Q", format=",.0f")])
        st.altair_chart(bars.properties(height=160).configure(background="transparent").configure_view(strokeWidth=0), use_container_width=True)
        st.caption("Most of the gain usually comes from the licence assumption, the one with the least evidence behind it. Move it to zero and see what is left.")
