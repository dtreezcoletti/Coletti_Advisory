from __future__ import annotations

OWNER_MAIN_NAV = (
    ("My Workspace", "⌂"),
    ("Case Queue", "▣"),
    ("Evidence", "◇"),
    ("Analysis", "⌁"),
    ("Human Review", "✓"),
    ("Reports", "▤"),
    ("Clients", "♙"),
    ("Messages", "◫"),
    ("Knowledge Base", "◧"),
)

OWNER_CONTROL_NAV = (
    ("Approvals", "✓"),
    ("Dispatcher", "⌘"),
    ("Team", "♙"),
    ("Financials", "$"),
    ("Firm Overview", "◔"),
    ("Settings", "⚙"),
)

OWNER_REFERENCE_CSS = r"""
<style>
/* 2026-09-08 owner-console reference standard ----------------------------- */
:root {
    --oc-paper: #f5f1e8;
    --oc-card: #fffefa;
    --oc-line: #ddd5c9;
    --oc-ink: #161817;
    --oc-muted: #777168;
    --oc-gold: #b18138;
    --oc-gold-deep: #8d642c;
    --oc-gold-soft: #f2e4cb;
    --oc-red-soft: #f8e2df;
    --oc-red: #a8524c;
    --oc-green-soft: #e6efe9;
    --oc-green: #4b7560;
    --oc-blue-soft: #e8eef2;
    --oc-blue: #58758a;
    --oc-shadow: 0 8px 24px rgba(39, 33, 24, .045);
    --oc-serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    --oc-sans: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.stApp { background: #f8f5ef; }
.block-container { max-width: 1520px; padding-top: .75rem; }

[data-testid="stSidebar"] {
    background: #f8f4ed !important;
    border-right: 1px solid #d9d0c4 !important;
    min-width: 226px !important;
    max-width: 226px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: .7rem .62rem 1.1rem !important; }
[data-testid="stSidebar"] .stButton > button {
    min-height: 2.38rem !important;
    border: 0 !important;
    border-radius: 5px !important;
    justify-content: flex-start !important;
    padding: .45rem .7rem !important;
    box-shadow: none !important;
    font-size: .79rem !important;
    color: #313230 !important;
    background: transparent !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #efe8dc !important; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #9d6f2d, #c7984e) !important;
    color: white !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    min-height: 2.25rem;
    border-radius: 5px !important;
    background: #fffdfa !important;
}

.oc-topbar {
    display:grid;
    grid-template-columns: 260px minmax(260px, 1fr) 255px;
    gap: 1rem;
    align-items:center;
    padding:.18rem .1rem .68rem;
}
.oc-topbrand { display:flex; align-items:baseline; gap:.75rem; }
.oc-topbrand strong { font-family:var(--oc-serif); font-size:1.45rem; font-weight:400; color:var(--oc-ink); }
.oc-topbrand span { font-size:.76rem; color:#5f605d; }
.oc-profile { display:flex; justify-content:flex-end; align-items:center; gap:.65rem; }
.oc-avatar {
    width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    background:#cdbda5; color:white; font-size:.72rem; font-weight:700;
}
.oc-profile-copy strong { display:block; font-size:.75rem; line-height:1.1; }
.oc-profile-copy span { font-size:.64rem; color:#8b877f; }
.oc-bell { font-size:1.05rem; color:#202220; }

.oc-search-shell div[data-baseweb="input"] > div {
    border-radius: 5px !important;
    background:#fffefa !important;
    border:1px solid #d7d1c7 !important;
    min-height:2.35rem !important;
}
.oc-search-shell input { font-size:.77rem !important; }

.oc-hero {
    min-height:186px;
    display:grid;
    grid-template-columns:minmax(0,1.7fr) minmax(320px,.95fr) 210px;
    overflow:hidden;
    border:1px solid #ddd6cb;
    border-radius:7px;
    background:#fbf8f2;
    box-shadow:var(--oc-shadow);
}
.oc-hero-copy { padding:1.75rem 1.9rem 1.55rem; position:relative; z-index:2; }
.oc-kicker { text-transform:uppercase; letter-spacing:.32em; font-size:.58rem; color:#9a7848; font-weight:700; }
.oc-hero h1 {
    font-family:var(--oc-serif) !important; font-size:clamp(2.65rem,4vw,4rem) !important;
    font-weight:400 !important; line-height:.98; letter-spacing:-.035em; margin:.35rem 0 .22rem;
}
.oc-hero-sub { font-family:var(--oc-serif); font-size:1.18rem; color:#30302d; margin-bottom:.25rem; }
.oc-hero-body { color:#6d6c67; font-size:.82rem; line-height:1.45; max-width:590px; }
.oc-hero-art {
    position:relative; min-height:186px; border-left:1px solid rgba(208,198,185,.55);
    background:
      linear-gradient(90deg,rgba(250,247,240,.30),rgba(255,255,255,.05)),
      linear-gradient(180deg,#d6cdbf 0 55%,#c8bca9 55% 58%,#eee8df 58% 100%);
}
.oc-hero-art:before {
    content:""; position:absolute; left:40%; bottom:38px; width:7px; height:118px; background:#726f5b;
    border-radius:999px; transform:rotate(-6deg);
    box-shadow:
      -34px -8px 0 -2px #626a4e,
      -21px -38px 0 -2px #687154,
      16px -54px 0 -2px #66704f,
      34px -29px 0 -2px #747d5c,
      24px 3px 0 -2px #5f684c,
      -37px 23px 0 -2px #6c7456;
}
.oc-hero-art:after {
    content:""; position:absolute; left:30%; right:20%; bottom:27px; height:34px;
    border:1px solid rgba(95,88,73,.22); background:rgba(244,241,234,.58);
    box-shadow: 18px 13px 0 rgba(81,72,57,.12);
}
.oc-hero-quote {
    position:relative; border-left:1px solid #c89b58; margin:2rem 1.25rem; padding:.1rem 0 .1rem 1rem;
    text-transform:uppercase; letter-spacing:.24em; line-height:2.05; font-size:.57rem; color:#4f4e49;
}

.oc-kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.65rem; margin:.72rem 0; }
.oc-kpi {
    background:var(--oc-card); border:1px solid var(--oc-line); border-radius:6px; padding:.8rem .88rem;
    min-height:86px; box-shadow:var(--oc-shadow);
}
.oc-kpi-row { display:flex; align-items:center; gap:.68rem; }
.oc-kpi-icon {
    width:38px; height:38px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    background:var(--oc-gold-soft); color:var(--oc-gold-deep); font-size:.92rem; flex:0 0 38px;
}
.oc-kpi-value { font-family:var(--oc-serif); font-size:1.45rem; line-height:1; color:var(--oc-ink); }
.oc-kpi-label { font-size:.70rem; font-weight:700; color:#353632; margin-top:.1rem; }
.oc-kpi-sub { font-size:.61rem; color:#8a857c; margin-top:.16rem; }

.oc-card {
    background:var(--oc-card); border:1px solid var(--oc-line); border-radius:6px;
    box-shadow:var(--oc-shadow); overflow:hidden;
}
.oc-card-head { display:flex; justify-content:space-between; align-items:center; padding:.68rem .82rem; border-bottom:1px solid #eee9e1; }
.oc-card-title { font-family:var(--oc-serif); font-size:1.02rem; }
.oc-link { font-size:.62rem; color:#946a2f; }
.oc-tabs { display:flex; gap:1.3rem; font-size:.61rem; color:#8b867c; }
.oc-tabs span:first-child { color:#946a2f; border-bottom:2px solid #a87a39; padding-bottom:.42rem; }
.oc-row {
    display:grid; grid-template-columns:28px minmax(145px,1.2fr) minmax(125px,1fr) auto 72px;
    align-items:center; gap:.55rem; padding:.55rem .74rem; border-bottom:1px solid #eee9e2; font-size:.67rem;
}
.oc-row:last-child { border-bottom:0; }
.oc-row-icon { width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f3e7d3; color:#9a6e2e; font-size:.68rem; }
.oc-row-title { font-weight:700; color:#40413e; }
.oc-row-sub { color:#818078; }
.oc-status { border-radius:999px; padding:.23rem .45rem; font-size:.57rem; white-space:nowrap; }
.oc-status.warn { background:#fbefd8; color:#986f31; }
.oc-status.alert { background:var(--oc-red-soft); color:var(--oc-red); }
.oc-status.ok { background:var(--oc-green-soft); color:var(--oc-green); }
.oc-time { color:#8c8982; font-size:.59rem; text-align:right; }

.oc-three { display:grid; grid-template-columns:1.08fr 1fr 1fr; gap:.65rem; margin-top:.65rem; }
.oc-mini-row { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:.5rem; align-items:center; padding:.55rem .74rem; border-bottom:1px solid #eee9e2; }
.oc-mini-row:last-child { border-bottom:0; }
.oc-mini-title { font-size:.67rem; font-weight:700; color:#44443f; }
.oc-mini-sub { font-size:.59rem; color:#8b877e; margin-top:.12rem; }
.oc-mini-meta { font-size:.58rem; color:#8c887f; white-space:nowrap; }

.oc-dari-header { display:flex; align-items:center; gap:.6rem; padding:.8rem .8rem .55rem; }
.oc-dari-orb { width:34px; height:34px; border-radius:50%; background:radial-gradient(circle,#65558a 0 18%,#b4a6cb 22%,#e7dfef 46%,#faf7fc 67%); box-shadow:0 0 18px rgba(111,91,148,.25); }
.oc-dari-title { font-family:var(--oc-serif); font-size:1.02rem; }
.oc-dari-sub { font-size:.59rem; color:#77726a; margin-left:.15rem; }
.oc-dari-copy { padding:0 .8rem .48rem; }
.oc-dari-copy strong { display:block; font-family:var(--oc-serif); font-size:.88rem; margin-bottom:.26rem; }
.oc-dari-copy span { font-size:.64rem; color:#78746c; }
.oc-alert-line { display:grid; grid-template-columns:24px 1fr; gap:.45rem; align-items:center; padding:.38rem .8rem; font-size:.64rem; }
.oc-alert-dot { width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f6e8dd; }
.oc-action-row { display:grid; grid-template-columns:28px 1fr auto; gap:.48rem; align-items:center; padding:.58rem .72rem; border-bottom:1px solid #eee9e2; }
.oc-action-row:last-child { border-bottom:0; }
.oc-action-icon { width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f3e6d3; color:#9a702e; font-size:.66rem; }
.oc-action-title { font-size:.66rem; font-weight:700; }
.oc-action-sub { font-size:.57rem; color:#8b867e; margin-top:.1rem; }
.oc-chevron { color:#98938a; }

.oc-day {
    background:linear-gradient(130deg,#f4ede2,#fffefa 60%); border:1px solid var(--oc-line); border-radius:7px;
    padding:1.5rem 1.5rem 1.25rem; box-shadow:var(--oc-shadow);
}
.oc-day h1 { font-size:clamp(2.4rem,4vw,3.8rem)!important; margin:.25rem 0 .2rem; }
.oc-day-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; margin-top:1rem; }
.oc-day-block { background:#fffefa; border:1px solid #e6dfd5; border-radius:6px; padding:.8rem; min-height:110px; }
.oc-day-block strong { font-family:var(--oc-serif); font-size:.92rem; font-weight:400; }
.oc-day-block p { font-size:.66rem; color:#77736c; line-height:1.45; }

@media (max-width: 1100px) {
    .oc-topbar { grid-template-columns:1fr; gap:.4rem; }
    .oc-profile { justify-content:flex-start; }
    .oc-hero { grid-template-columns:1fr minmax(260px,.8fr); }
    .oc-hero-quote { display:none; }
    .oc-kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .oc-three { grid-template-columns:1fr; }
    .oc-day-grid { grid-template-columns:1fr 1fr; }
}
@media (max-width: 820px) {
    [data-testid="stSidebar"] { min-width:min(88vw,340px)!important; max-width:min(88vw,340px)!important; }
    .block-container { padding-left:.7rem!important; padding-right:.7rem!important; }
    .oc-hero { grid-template-columns:1fr; }
    .oc-hero-art { min-height:92px; border-left:0; border-top:1px solid var(--oc-line); }
    .oc-kpi-grid { grid-template-columns:1fr 1fr; gap:.48rem; }
    .oc-row { grid-template-columns:28px minmax(0,1fr) auto; }
    .oc-row .oc-row-sub, .oc-row .oc-time { display:none; }
    .oc-day-grid { grid-template-columns:1fr; }
}
</style>
"""

