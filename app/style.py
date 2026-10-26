"""Look and feel: a photographer's light table. Recommendations are 35mm film frames; how bright a frame is tells you how
exposed that title already is (head = fully exposed, tail = underexposed). Red grease-pencil circles mark picks and hits."""
import html

INK, ACETATE, GREASE, FIXER = "#20332f", "#294740", "#c65d4b", "#648b78"
FRAME = {"head": ("#f4e7c8", INK), "mid": ("#c4d0c5", INK), "tail": ("#344943", "#f8f4e9")}      # background, text per tier
TIER_WORD = {"head": "head", "mid": "mid", "tail": "tail"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {{ --ink:{INK}; --green:{ACETATE}; --accent:{GREASE}; --sage:{FIXER}; --paper:#f7f6f1; --line:#dce3dc; }}
html, body, [class*="css"], .stApp {{ font-family:'DM Sans',sans-serif; color:var(--ink); }}
.stApp {{ background:linear-gradient(135deg,#f8f8f4 0%,#f0f3ee 55%,#e9efea 100%); }}
header[data-testid="stHeader"] {{ background:rgba(248,248,244,.88); }}
footer, #MainMenu {{ visibility:hidden; }}
.block-container {{ padding-top:2rem; padding-bottom:3rem; max-width:1320px; }}
h1,h2,h3,h4 {{ font-family:'Space Grotesk',sans-serif; color:var(--ink); letter-spacing:-.035em; }}
h1 {{ font-size:clamp(2rem,4vw,3.3rem); font-weight:700; }}
h2 {{ font-weight:700; }}
p,li,label,.stMarkdown {{ line-height:1.65; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color:#53655d !important; }}
/* Sidebar: high contrast, clear hierarchy */
section[data-testid="stSidebar"] {{ background:#edf1eb; border-right:1px solid #d5ded5; }}
section[data-testid="stSidebar"] > div {{ padding-top:1.5rem; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"], section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] span {{ color:#20332f !important; }}
section[data-testid="stSidebar"] h3 {{ font-size:1.15rem; margin-top:1.1rem; }}
section[data-testid="stSidebar"] [data-testid="stSlider"] {{ padding: .4rem 0; }}
section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{ background:var(--accent); border-color:white; }}
section[data-testid="stSidebar"] [data-baseweb="slider"] > div > div {{ background:var(--accent); }}
/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; border-bottom:1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ font-family:'DM Sans',sans-serif; font-weight:700; padding:12px 17px; border-radius:10px 10px 0 0; color:#52635b; }}
.stTabs [aria-selected="true"] {{ background:var(--green); color:#fff !important; }}
.stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] div {{ color:#fff !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ background:var(--green); }}
/* Controls */
.stButton button {{ font-family:'DM Sans',sans-serif; font-weight:700; border:1px solid #cbd7cd; border-radius:10px; background:#fff; color:var(--ink); min-height:2.65rem; transition:all .15s ease; }}
.stButton button:hover {{ background:var(--green); color:white; border-color:var(--green); transform:translateY(-1px); }}
.stButton button:focus-visible, .stTabs [data-baseweb="tab"]:focus-visible {{ outline:3px solid var(--accent); outline-offset:2px; }}
[data-baseweb="select"] > div, [data-baseweb="input"] > div {{ border-radius:10px; border-color:#cbd7cd; }}
[data-testid="stMultiSelect"] [data-baseweb="select"] {{ background:white; border-radius:10px; }}
[data-testid="stExpander"] {{ border:1px solid var(--line); border-radius:12px; background:rgba(255,255,255,.65); }}
hr {{ border-color:var(--line); }}
/* Hero */
.masthead {{ display:flex; align-items:flex-end; gap:20px; flex-wrap:wrap; margin:0 0 1.4rem; padding:1.5rem 1.6rem; border-radius:18px; background:linear-gradient(115deg,#203b34,#294740 70%,#426b5c); color:#f7f6f1; box-shadow:0 12px 30px rgba(32,51,47,.12); }}
.masthead .stamp {{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:clamp(1.8rem,3.4vw,2.8rem); letter-spacing:-.05em; line-height:1.05; color:#fff; }}
.masthead .sub {{ max-width:52ch; color:#e3ebe4; font-size:1rem; }}
.note {{ font-family:'DM Sans',sans-serif; font-weight:700; color:var(--accent); font-size:1rem; line-height:1.3; }}
.small {{ font-size:.9rem; color:#53655d; }}
/* Filmstrip motif retained, refined */
.reel {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:0; margin:10px 0 8px; }}
@media(max-width:900px){{.reel{{grid-template-columns:repeat(3,minmax(0,1fr));}}}}
@media(max-width:560px){{.reel{{grid-template-columns:repeat(2,minmax(0,1fr));}} .block-container{{padding-left:1rem;padding-right:1rem;}}}}
.cell {{ display:flex; flex-direction:column; min-width:0; }}
.cell .acetate {{ background:var(--green); padding:15px 5px; position:relative; }}
.cell .acetate::before,.cell .acetate::after {{ content:""; position:absolute; left:0; right:0; height:7px; background-image:repeating-linear-gradient(90deg,#f7f6f1 0 9px,transparent 9px 20px); opacity:.95; }}
.cell .acetate::before{{top:4px;}} .cell .acetate::after{{bottom:4px;}}
.frame {{ position:relative; min-height:132px; padding:12px 11px 10px; display:flex; flex-direction:column; justify-content:space-between; border-radius:5px; overflow:visible; }}
.frame.empty {{ background:rgba(255,255,255,.12); border:1px dashed #9aafa2; color:#d9e2db; }}
.frame .no {{ position:absolute; top:6px; right:9px; font:700 11px 'DM Sans',sans-serif; opacity:.65; }}
.frame .t {{ font:700 14px/1.25 'Space Grotesk',sans-serif; padding-right:13px; display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }}
.frame .meta {{ font-size:11px; opacity:.9; display:flex; justify-content:space-between; gap:5px; }}
.frame.hit::after,.frame.pick::after {{ content:""; position:absolute; inset:-7px -3px; border:3px solid var(--accent); border-radius:16px 24px 18px 26px / 20px 16px 24px 18px; transform:rotate(-1.6deg); pointer-events:none; z-index:3; }}
.cell .why {{ min-height:30px; padding:7px 6px 0; }}
.xbar {{ display:flex; height:27px; border:1px solid var(--line); border-radius:7px; overflow:hidden; background:white; }}
.xbar span {{ display:flex; align-items:center; justify-content:center; font:700 12px 'DM Sans',sans-serif; white-space:nowrap; overflow:hidden; }}
.xrow {{ display:grid; grid-template-columns:170px 1fr; gap:12px; align-items:center; margin:9px 0; }}
.xrow .lab {{ font:700 13px 'DM Sans',sans-serif; }}
@media(max-width:640px){{.xrow{{grid-template-columns:1fr;gap:4px;}}}}
.readouts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:12px 0 6px; }}
.readouts > div {{ background:rgba(255,255,255,.75); border:1px solid var(--line); border-radius:13px; padding:16px; }}
.readouts .k {{ font-size:.85rem; color:#53655d; }}
.readouts .v {{ font:700 1.8rem/1.15 'Space Grotesk',sans-serif; letter-spacing:-.04em; color:var(--ink); overflow-wrap:anywhere; }}
.readouts .d {{ font-size:.82rem; font-weight:700; color:var(--sage); margin-top:5px; }} .readouts .d.bad{{color:var(--accent);}}
.verdict {{ background:#eef4ee; border:1px solid #d7e3d8; border-left:5px solid var(--accent); border-radius:0 12px 12px 0; padding:13px 16px; margin:12px 0; }}
[data-testid="stAlert"] {{ border-radius:12px; }}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important;}}}}
</style>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def strip(items, recs, hits=(), picks=(), notes=None, pad_to=None, cols=None):
    """One film strip. recs = item indices. hits/picks = indices to ring in red. notes = optional handwritten line under each frame."""
    hits, picks = set(int(i) for i in hits), set(int(i) for i in picks)
    group, title, genres = items["group"].to_numpy(), items["title"].to_numpy(), items["genres"].to_numpy()
    cells = []
    for rank, i in enumerate(recs, 1):
        i = int(i)
        bg, fg = FRAME[group[i]]
        cls = "frame" + (" hit" if i in hits else "") + (" pick" if i in picks else "")
        name, _, year = title[i].rpartition(" (")
        name, year = (name, year.rstrip(")")) if name else (title[i], "")
        g = genres[i].split("|")[0]
        why = f"<div class='note'>{esc(notes[rank - 1])}</div>" if notes else ""
        cells.append(f"<div class='cell'><div class='acetate'><div class='{cls}' style='background:{bg};color:{fg}'>"
                     f"<span class='no'>{rank}</span><div class='t'>{esc(name)}</div>"
                     f"<div class='meta'><span>{esc(year)}</span><span>{TIER_WORD[group[i]]} · {esc(g)}</span></div></div></div>"
                     f"<div class='why'>{why}</div></div>")
    for k in range(len(recs), pad_to or 0):                      # empty frames waiting to be filled
        cells.append(f"<div class='cell'><div class='acetate'><div class='frame empty'>"
                     f"<div class='t'>{'pick a movie' if k == len(recs) else ''}</div><span class='no'>{k + 1}</span></div></div><div class='why'></div></div>")
    grid = f" style='grid-template-columns:repeat({cols},1fr)'" if cols else ""
    return f"<div class='reel'{grid}>" + "".join(cells) + "</div>"


def exposure_bar(label, share, bold=False):
    """share = dict head/mid/tail -> fraction. Segment colour = frame colour, so the bar reads like the strip above it."""
    segs = []
    for g in ("head", "mid", "tail"):
        v = share.get(g, 0.0)
        if v <= 0: continue
        bg, fg = FRAME[g]
        segs.append(f"<span style='width:{v * 100:.1f}%;background:{bg};color:{fg}'>{v:.0%}</span>" if v >= 0.07 else
                    f"<span style='width:{v * 100:.1f}%;background:{bg};color:{fg}'></span>")
    w = "font-weight:800" if bold else ""
    return f"<div class='xrow'><div class='lab' style='{w}'>{esc(label)}</div><div class='xbar'>{''.join(segs)}</div></div>"


def readouts(rows):
    """rows = [(label, value_text, delta_text, bad_bool)]"""
    out = []
    for lab, val, delta, bad in rows:
        d = f"<div class='d{' bad' if bad else ''}'>{esc(delta)}</div>" if delta else ""
        out.append(f"<div><div class='k'>{esc(lab)}</div><div class='v'>{esc(val)}</div>{d}</div>")
    return "<div class='readouts'>" + "".join(out) + "</div>"
