from __future__ import annotations

import streamlit as st


LUXURY_THEME_CSS = r"""
<style>
/* Coletti & Co. — restrained luxury / boutique professional services ----------
   Quiet, editorial, high-trust. No fintech neon, no glossy SaaS gradients. */
:root {
    --cc-ink: #171715;
    --cc-ink-soft: #2a2926;
    --cc-muted: #716d65;
    --cc-muted-2: #928c82;
    --cc-paper: #f6f3ed;
    --cc-paper-deep: #efebe3;
    --cc-card: #fffdf9;
    --cc-line: #dcd5ca;
    --cc-line-dark: #c9c0b3;
    --cc-brass: #94703b;
    --cc-brass-deep: #75562d;
    --cc-brass-soft: #eee5d7;
    --cc-green: #486153;
    --cc-green-soft: #e8eee9;
    --cc-rose: #8b645c;
    --cc-shadow: 0 12px 36px rgba(28, 26, 22, .045);
    --cc-shadow-float: 0 18px 48px rgba(28, 26, 22, .075);
    --cc-radius: 5px;
    --cc-serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    --cc-sans: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--cc-sans);
    color: var(--cc-ink);
}

.stApp {
    background:
        linear-gradient(rgba(255,255,255,.16), rgba(255,255,255,.16)),
        var(--cc-paper);
    color: var(--cc-ink);
}

.block-container {
    max-width: 1440px;
    padding-top: 1.45rem;
    padding-bottom: 4rem;
}

h1, h2, h3, .cc-serif {
    font-family: var(--cc-serif) !important;
    color: var(--cc-ink);
    letter-spacing: -.028em;
    font-weight: 400 !important;
}

h1 { line-height: 1.02; }
h2, h3 { line-height: 1.14; }

p, li, label, [data-testid="stCaptionContainer"] {
    color: var(--cc-ink-soft);
}

[data-testid="stHeader"] {
    background: rgba(246, 243, 237, .94);
    border-bottom: 1px solid rgba(201, 192, 179, .62);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
}

[data-testid="stToolbar"] { right: 1rem; }

/* Sidebar — editorial, not dashboard-heavy. */
[data-testid="stSidebar"] {
    background: #f2eee7;
    border-right: 1px solid var(--cc-line-dark);
    min-width: 258px;
    max-width: 258px;
}

[data-testid="stSidebar"] > div:first-child { padding-top: .85rem; }
[data-testid="stSidebar"] hr { border-color: var(--cc-line); }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .1rem; }

[data-testid="stSidebar"] [role="radiogroup"] label {
    position: relative;
    padding: .68rem .78rem;
    border-radius: 2px;
    transition: background .12s ease, color .12s ease;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(255, 253, 249, .72);
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: #1d1d1b;
    color: #fbf8f2;
    box-shadow: none;
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {
    content: "";
    position: absolute;
    left: 0;
    top: .5rem;
    bottom: .5rem;
    width: 2px;
    background: #b3925f;
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
    color: #fbf8f2 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] input { display: none; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    border-color: var(--cc-line-dark);
    background: var(--cc-card);
    border-radius: var(--cc-radius);
}

/* Inputs and controls */
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
    border-color: var(--cc-line-dark) !important;
    background: var(--cc-card) !important;
    border-radius: var(--cc-radius) !important;
    box-shadow: none !important;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    border-radius: 3px !important;
    border: 1px solid var(--cc-line-dark) !important;
    min-height: 2.65rem;
    font-weight: 600;
    letter-spacing: .01em;
    box-shadow: none !important;
    background: var(--cc-card);
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: #aaa092 !important;
    background: #faf7f1 !important;
}

.stButton > button[kind="primary"] {
    background: #1c1d1c !important;
    color: #fffdf9 !important;
    border-color: #1c1d1c !important;
}

/* Native cards */
[data-testid="stMetric"],
[data-testid="stDataFrame"],
div[data-testid="stExpander"] {
    background: var(--cc-card);
    border: 1px solid var(--cc-line);
    border-radius: var(--cc-radius);
    box-shadow: var(--cc-shadow);
}

[data-testid="stMetric"] { padding: 1rem 1.05rem; }
[data-testid="stDataFrame"] { overflow: hidden; }
div[data-testid="stExpander"] { overflow: hidden; }

div[data-testid="stTabs"] button {
    font-weight: 600;
    letter-spacing: .005em;
}

/* Brand lockup */
.cc-logo { padding: .35rem .24rem 1rem; }
.cc-logo-name {
    font-family: var(--cc-serif);
    font-size: 1.62rem;
    line-height: 1;
    letter-spacing: -.035em;
    color: var(--cc-ink);
}
.cc-logo-tag {
    margin-top: .32rem;
    font-size: .49rem;
    color: #80786d;
    letter-spacing: .31em;
    text-transform: uppercase;
    font-weight: 700;
}

/* Page topline */
.cc-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: .05rem 0 1.05rem;
    padding-bottom: .72rem;
    border-bottom: 1px solid var(--cc-line);
}
.cc-topline-title {
    font-family: var(--cc-serif);
    font-size: 1.16rem;
    letter-spacing: -.015em;
}
.cc-pill {
    border: 1px solid var(--cc-line-dark);
    background: rgba(255,253,249,.78);
    border-radius: 999px;
    padding: .39rem .72rem;
    color: #686259;
    font-size: .7rem;
    letter-spacing: .015em;
}

.cc-kicker {
    color: var(--cc-brass-deep);
    text-transform: uppercase;
    letter-spacing: .30em;
    font-size: .61rem;
    font-weight: 700;
}

/* Hero — private-client service firm, not software landing page. */
.cc-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.42fr) minmax(250px, .58fr);
    min-height: 226px;
    border: 1px solid var(--cc-line-dark);
    border-radius: 3px;
    overflow: hidden;
    background: #f9f6f0;
    box-shadow: var(--cc-shadow);
    margin-bottom: 1.05rem;
}

.cc-hero-copy { padding: 2.45rem 2.55rem 2.35rem; }
.cc-hero h1 {
    font-size: clamp(2.45rem, 4.2vw, 4.3rem);
    margin: .42rem 0 .35rem;
    line-height: .95;
}
.cc-hero-sub {
    font-family: var(--cc-serif);
    font-size: 1.22rem;
    margin: .3rem 0 .6rem;
    color: #393631;
}
.cc-hero-body {
    color: var(--cc-muted);
    max-width: 680px;
    line-height: 1.65;
    font-size: .88rem;
}

.cc-hero-art {
    position: relative;
    min-height: 226px;
    border-left: 1px solid rgba(201, 192, 179, .7);
    background:
        linear-gradient(155deg, rgba(255,255,255,.78), rgba(255,255,255,.08)),
        repeating-linear-gradient(90deg, transparent 0 38px, rgba(148,112,59,.035) 38px 39px),
        #e9e2d7;
}

.cc-hero-art:before {
    content: "";
    position: absolute;
    left: 18%;
    right: 18%;
    top: 24%;
    height: 1px;
    background: #aa8a5a;
    box-shadow: 0 52px 0 rgba(117,86,45,.35), 0 104px 0 rgba(117,86,45,.18);
}

.cc-hero-art:after {
    content: "RECORDS\A CLARITY\A JUDGMENT\A FORWARD";
    white-space: pre;
    position: absolute;
    right: 1.55rem;
    top: 2.1rem;
    width: 8.5rem;
    padding-left: .9rem;
    border-left: 1px solid #a48250;
    color: #575148;
    line-height: 2.15;
    letter-spacing: .22em;
    font-size: .56rem;
    font-weight: 700;
}

/* KPI grid */
.cc-grid-4 {
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: .78rem;
    margin: .82rem 0 1.05rem;
}
.cc-stat {
    background: var(--cc-card);
    border: 1px solid var(--cc-line);
    border-radius: var(--cc-radius);
    padding: 1.05rem 1.08rem;
    box-shadow: var(--cc-shadow);
    min-height: 102px;
}
.cc-stat-row { display: flex; align-items: center; gap: .82rem; }
.cc-stat-icon {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #ddcfbb;
    background: #f3ece1;
    color: #876332;
    font-size: 1rem;
}
.cc-stat-value {
    font-family: var(--cc-serif);
    font-size: 1.76rem;
    line-height: 1;
    letter-spacing: -.025em;
}
.cc-stat-label {
    font-size: .7rem;
    color: var(--cc-muted);
    margin-top: .28rem;
    letter-spacing: .01em;
}

/* Panels */
.cc-panel {
    background: var(--cc-card);
    border: 1px solid var(--cc-line);
    border-radius: var(--cc-radius);
    padding: 1.12rem 1.22rem;
    box-shadow: var(--cc-shadow);
    margin: .78rem 0;
}
.cc-panel-title {
    font-family: var(--cc-serif);
    font-size: 1.16rem;
    margin-bottom: .8rem;
    letter-spacing: -.015em;
}

/* Engagement progress */
.cc-stage-wrap {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: .3rem;
    padding: .62rem .15rem .22rem;
}
.cc-stage { flex: 1; text-align: center; min-width: 0; position: relative; }
.cc-stage:not(:last-child):after {
    content: "";
    position: absolute;
    top: 10px;
    left: 60%;
    width: 80%;
    height: 1px;
    background: #d6d0c7;
    z-index: 0;
}
.cc-stage.done:not(:last-child):after { background: #708477; }
.cc-stage-dot {
    width: 21px;
    height: 21px;
    border-radius: 50%;
    margin: 0 auto .48rem;
    background: #d2cec7;
    border: 4px solid #f3f0ea;
    position: relative;
    z-index: 1;
}
.cc-stage.done .cc-stage-dot { background: #587062; border-color: #e7ece8; }
.cc-stage.current .cc-stage-dot {
    background: #98713a;
    border-color: #eee3d2;
    box-shadow: 0 0 0 1px #98713a;
}
.cc-stage-name { font-size: .68rem; font-weight: 700; }
.cc-stage-status { font-size: .58rem; color: #908b83; margin-top: .22rem; }

.cc-list-row {
    display: grid;
    grid-template-columns: 30px minmax(0,1fr) auto;
    align-items: center;
    gap: .68rem;
    padding: .7rem .08rem;
    border-bottom: 1px solid #ece7df;
}
.cc-list-row:last-child { border-bottom: none; }
.cc-list-icon {
    width: 27px;
    height: 27px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #d9ddd9;
    background: #edf1ed;
    color: #526a5c;
    font-size: .72rem;
}
.cc-list-title { font-size: .79rem; font-weight: 700; }
.cc-list-sub { font-size: .66rem; color: #8a857d; margin-top: .14rem; }
.cc-status {
    font-size: .62rem;
    padding: .24rem .52rem;
    border-radius: 999px;
    border: 1px solid #d5dfd8;
    background: var(--cc-green-soft);
    color: #486151;
    white-space: nowrap;
}

/* Owner console stays sober and powerful, not flashy. */
.cc-owner-banner {
    background: #1b1c1b;
    color: #f5f1e9;
    border: 1px solid #2d2e2c;
    border-radius: 3px;
    padding: 1.08rem 1.25rem;
    margin-bottom: 1.05rem;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    box-shadow: var(--cc-shadow-float);
}
.cc-owner-banner strong {
    font-family: var(--cc-serif);
    font-size: 1.24rem;
    font-weight: 400;
}
.cc-owner-banner span { color: #cbc6bc; font-size: .72rem; }
.cc-small { color: var(--cc-muted); font-size: .74rem; }

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(255,253,249,.7);
    border: 1px dashed #bfb5a7;
    border-radius: var(--cc-radius);
}

@media (max-width: 1000px) {
    .cc-grid-4 { grid-template-columns: repeat(2,minmax(0,1fr)); }
    .cc-hero { grid-template-columns: 1fr; }
    .cc-hero-art { min-height: 118px; border-left: 0; border-top: 1px solid var(--cc-line); }
    .cc-stage-wrap { overflow-x: auto; justify-content: flex-start; }
    .cc-stage { min-width: 115px; }
}

@media (max-width: 650px) {
    .block-container { padding-left: .8rem; padding-right: .8rem; }
    .cc-grid-4 { grid-template-columns: 1fr 1fr; gap: .55rem; }
    .cc-hero-copy { padding: 1.5rem 1.3rem; }
    .cc-hero h1 { font-size: 2.4rem; }
    .cc-topline { align-items: flex-start; flex-direction: column; }
}
</style>
"""


def apply_luxury_theme() -> None:
    st.markdown(LUXURY_THEME_CSS, unsafe_allow_html=True)
