"""Core logic for the 'Blockbusted' demo. Pure NumPy/pandas - no Streamlit - so it can be tested on its own."""
import json
import numpy as np
import pandas as pd
from scipy import sparse
from pathlib import Path


def load_artifacts(art_dir="artifacts"):
    d = Path(art_dir)
    z = np.load(d / "pools.npz")
    A = {k: z[k] for k in z.files}
    A["items"] = pd.read_csv(d / "items.csv")
    A["hist"] = sparse.load_npz(d / "history.npz").tocsr()
    A["future"] = sparse.load_npz(d / "future.npz").tocsr()
    A["pop"] = pd.read_csv(d / "pop_metrics.csv")
    A["meta"] = json.load(open(d / "meta.json"))
    A["Gn"] = A["G"] / A["G"].sum(axis=1, keepdims=True)
    A["user_pos"] = {int(u): i for i, u in enumerate(A["users"])}
    f = d / "factors.npz"                                   # item factors for the "pick your own movies" feature
    A["has_factors"] = f.exists()
    if A["has_factors"]:
        zf = np.load(f)
        A.update(Q_base=zf["Q_base"], Q_mit=zf["Q_mit"], w_mit=zf["w_mit"], reg=float(zf["reg"]), alpha=float(zf["alpha"]),
                 QtQ_base=zf["QtQ_base"] if "QtQ_base" in zf.files else None, QtQ_mit=zf["QtQ_mit"] if "QtQ_mit" in zf.files else None)
        Q = A["Q_mit"]
        A["Qn_mit"] = Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9)
    A["demand"] = demand_share(A)
    if A["has_factors"]:
        A["coords"] = map_coords(A["Q_mit"])
    A["loop"] = pd.read_csv(d / "loop.csv") if (d / "loop.csv").exists() else None
    A["biz"] = json.load(open(d / "business.json")) if (d / "business.json").exists() else None
    return A


def demand_share(A):
    """What viewers really liked later (held-out window): share going to head / mid / tail titles."""
    g = A["items"]["group"].to_numpy()[A["future"].indices]
    return {k: float((g == k).mean()) for k in ("head", "mid", "tail")}


def map_coords(Q):
    """2-D 'map of the catalog': the first two principal components of the item factors."""
    X = Q - Q.mean(axis=0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    return (X @ vt[:2].T).astype(np.float32)


def list_share(A, recs):
    g = A["items"]["group"].to_numpy()[np.asarray(recs, dtype=int)]
    return {k: float((g == k).mean()) for k in ("head", "mid", "tail")}


def rerank_one(idx, sc, p, Gn, lam, K=10, alpha=0.01):
    """Calibrated greedy re-ranking for ONE user (same algorithm as the notebook's rerank_calibrated).
    idx/sc: the candidate pool (best first) and its model scores; p: the user's genre profile; lam=0 returns the model's own top-K."""
    idx = idx.astype(np.int64)
    rel = (sc - sc.min()) / (sc.max() - sc.min() + 1e-9)
    CG = Gn[idx]
    logp = np.log(np.where(p > 0, p, 1.0))
    S = np.zeros_like(p)
    chosen = np.zeros(len(idx), bool)
    out = np.empty(K, np.int64)
    for k in range(K):
        q = (S[None, :] + CG) / (k + 1)
        qs = np.maximum((1 - alpha) * q + alpha * p[None, :], 1e-12)
        kl = (p[None, :] * (logp[None, :] - np.log(qs))).sum(axis=1)
        obj = (1 - lam) * rel - lam * kl
        obj[chosen] = -np.inf
        j = int(obj.argmax())
        out[k] = idx[j]
        chosen[j] = True
        S += CG[j]
    return out


def user_lists(A, user_id, lam):
    """Standard (ALS) list and mitigated list (inverse-popularity ALS pool + calibrated re-ranking at strength lam)."""
    r = A["user_pos"][int(user_id)]
    K = A["meta"]["K"]
    std = A["base_idx"][r, :K].astype(np.int64)
    mit = rerank_one(A["mit_idx"][r], A["mit_sc"][r], A["p"][r], A["Gn"], lam, K)
    return std, mit


def list_stats(A, recs, p, future=()):
    """Metrics of one list. p = the genre profile the list is compared with; future = titles that count as hits (optional)."""
    items, G, Gn = A["items"], A["G"], A["Gn"]
    future = set(future)
    V = G[recs]
    V = V / np.linalg.norm(V, axis=1, keepdims=True)
    K = len(recs)
    ild = 1 - ((V @ V.T).sum() - K) / (K * (K - 1))
    groups = items["group"].to_numpy()[recs]
    tvd = 0.5 * np.abs(p - Gn[recs].mean(axis=0)).sum() if p.sum() > 0 else np.nan
    hits = sum(int(i) in future for i in recs)
    return {"hits": int(hits), "precision": hits / K,
            "head": int((groups == "head").sum()), "mid": int((groups == "mid").sum()), "tail": int((groups == "tail").sum()),
            "avg_pop_pct": float(items["pop_pct"].to_numpy()[recs].mean()), "ILD": float(ild), "genre_mismatch": float(tvd)}


def list_metrics(A, user_id, recs):
    """Metrics of one list for one MovieLens user. 'hits' = titles the user actually liked later (held-out window)."""
    r = A["user_pos"][int(user_id)]
    return list_stats(A, recs, A["p"][r], A["future"][r].indices.tolist())


def user_profile(A, user_id, n_titles=8, seed=0):
    """What the user liked before the test window: a reproducible sample of titles and the top genres of their taste profile."""
    r = A["user_pos"][int(user_id)]
    liked = A["hist"][r].indices
    rng = np.random.default_rng(seed)
    sample = rng.choice(liked, size=min(n_titles, len(liked)), replace=False) if len(liked) else np.array([], int)
    prof = pd.Series(A["p"][r], index=A["meta"]["genres"]).sort_values(ascending=False)
    return {"n_liked": int(len(liked)), "n_future": int(A["future"][r].nnz), "sample": A["items"].iloc[sample]["title"].tolist(),
            "sample_idx": [int(i) for i in sample],
            "top_genres": prof[prof > 0].head(5)}


def population_row(A, lam):
    """Population metrics (all test users) for the slider position closest to lam, plus the standard row."""
    pop = A["pop"]
    mit = pop[pop.setting == "mitigated"]
    row = mit.iloc[(mit.lam - lam).abs().argmin()]
    return pop[pop.setting == "standard"].iloc[0], row


# ---------------------------------------------------------------- "pick your own movies" (new user, cold start)
def foldin_user(Q, liked, w, reg, alpha, QtQ=None):
    """User vector for someone who liked the items in `liked`, with the item factors Q held fixed (one ALS user update).
    QtQ = Q'Q over the FULL catalog when the app only holds a subset of the titles (falls back to the subset)."""
    Yu = Q[liked]
    a = alpha * w[liked]
    A_ = (Q.T @ Q if QtQ is None else QtQ) + (Yu * a[:, None]).T @ Yu + reg * np.eye(Q.shape[1])
    return np.linalg.solve(A_, ((1 + a)[:, None] * Yu).sum(axis=0))


def recommend_for_picks(A, picks, lam, K=10, pool=100):
    """Recommendations for a brand-new user who picked some titles.
    standard = ALS fold-in, top K.  mitigated = inverse-popularity ALS fold-in, top `pool` candidates, calibrated re-ranking at lam."""
    picks = np.array(sorted({int(i) for i in picks}))
    n_items = A["Q_base"].shape[0]
    s_b = foldin_user(A["Q_base"], picks, np.ones(n_items, np.float32), A["reg"], A["alpha"], A.get("QtQ_base")) @ A["Q_base"].T
    s_m = foldin_user(A["Q_mit"], picks, A["w_mit"], A["reg"], A["alpha"], A.get("QtQ_mit")) @ A["Q_mit"].T
    s_b[picks] = -np.inf
    s_m[picks] = -np.inf
    std = np.argsort(-s_b)[:K]
    idx = np.argsort(-s_m)[:pool]
    p = A["Gn"][picks].mean(axis=0)                          # the user's genre taste = average genre mix of their picks
    mit = rerank_one(idx, s_m[idx], p, A["Gn"], lam, K)
    return std, mit, p


def because_of(A, picks, recs):
    """For each recommended title, the picked title it is most similar to (cosine similarity of item factors)."""
    picks = np.array(sorted({int(i) for i in picks}))
    sims = A["Qn_mit"][recs] @ A["Qn_mit"][picks].T
    return [A["items"]["title"].iloc[int(picks[j])] for j in sims.argmax(axis=1)]


def pick_summary(A, picks):
    """How mainstream is the user's taste? Share of their picks in head / mid / tail."""
    g = A["items"]["group"].to_numpy()[np.array(sorted({int(i) for i in picks}))]
    return {k: float((g == k).mean()) for k in ("head", "mid", "tail")}


# ---------------------------------------------------------------- the feedback loop and the business what-if
def business_case(B, **over):
    """Annual value of the mitigated pipeline vs the baseline. B = business.json. Every input can be overridden by keyword."""
    a = {r["key"]: r["base"] for r in B["assume"]}
    a.update(over)
    sim = B["sim"]
    value_per_sub = a["arpu"] * 12 * a["margin"]
    pp = lambda p: a["subs"] * (p / 100) * value_per_sub
    d_eng_pp = a["eng_churn_per_pct"] * sim["click_pct"]
    d_div_pp = a["div_churn_per_10pct"] * sim["eff_pct"] / 10
    newly = (sim["cov_mit"] - sim["cov_base"]) / 100 * B["n_titles"]
    lic = newly * a["licensed_share"] * a["license_cost"] * a["util_recovery"]
    out = {"engagement": pp(d_eng_pp), "retention": pp(d_div_pp), "licence": lic}
    out["net"] = sum(out.values())
    out["net_pct_revenue"] = 100 * out["net"] / (a["subs"] * a["arpu"] * 12)
    unit = pp(1) * sim["eff_pct"] / 10
    out["breakeven_excl_licence"] = -out["engagement"] / unit
    return out


def money(x):
    return f"${x / 1e6:,.2f}M" if abs(x) >= 1e6 else f"${x / 1e3:,.0f}K"


def random_viewer(A, rng, lam, n_sample=6):
    """A random MovieLens viewer, their taste sample, and the two lists. Which list is shown as A or B is shuffled by the caller."""
    uid = int(rng.choice(A["users"]))
    std, mit = user_lists(A, uid, lam)
    prof = user_profile(A, uid, n_titles=n_sample, seed=int(rng.integers(1_000_000)))
    r = A["user_pos"][uid]
    return {"uid": uid, "std": std, "mit": mit, "profile": prof, "future": set(A["future"][r].indices.tolist())}
