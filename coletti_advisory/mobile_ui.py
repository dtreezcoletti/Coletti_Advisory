from __future__ import annotations

import streamlit as st


MOBILE_CSS = r"""
<style>
/* Coletti & Co. mobile shell -------------------------------------------------
   Streamlit remains the application/runtime. This layer only changes layout,
   density, touch targets, and the sidebar drawer at tablet/phone widths. */

@media (max-width: 820px) {
    :root {
        --cc-mobile-gutter: .82rem;
        --cc-mobile-radius: 12px;
        --cc-mobile-shadow: 0 8px 24px rgba(25, 27, 26, .055);
    }

    html, body { overscroll-behavior-y: none; }

    [data-testid="stAppViewContainer"] {
        background: var(--cc-paper);
    }

    [data-testid="stHeader"] {
        height: 3.25rem;
        background: rgba(251, 250, 247, .96);
        border-bottom: 1px solid var(--cc-line);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    [data-testid="stToolbar"] {
        right: .35rem;
        top: .25rem;
    }

    .block-container {
        max-width: 100%;
        padding: .72rem var(--cc-mobile-gutter) calc(5rem + env(safe-area-inset-bottom));
    }

    /* The native Streamlit sidebar becomes the mobile navigation drawer. */
    [data-testid="stSidebar"] {
        width: min(89vw, 355px) !important;
        min-width: min(89vw, 355px) !important;
        max-width: min(89vw, 355px) !important;
        border-right: 1px solid var(--cc-line);
        box-shadow: 18px 0 45px rgba(18, 20, 19, .12);
        background: rgba(253, 252, 249, .985);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: .82rem .78rem calc(1rem + env(safe-area-inset-bottom));
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        min-height: 48px;
        padding: .75rem .82rem;
        border-radius: 10px;
        display: flex;
        align-items: center;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        min-height: 46px;
        border-radius: 10px;
    }

    .cc-logo {
        padding: .25rem .12rem .8rem;
    }

    .cc-logo-name {
        font-size: 1.55rem;
    }

    .cc-logo-tag {
        font-size: .5rem;
        letter-spacing: .24em;
    }

    /* Compact mobile app bar under Streamlit's native header. */
    .cc-topline {
        position: sticky;
        top: 3.25rem;
        z-index: 20;
        margin: -.72rem calc(var(--cc-mobile-gutter) * -1) .72rem;
        padding: .7rem var(--cc-mobile-gutter);
        min-height: 3.25rem;
        flex-direction: row;
        align-items: center;
        gap: .55rem;
        background: rgba(251, 250, 247, .965);
        border-bottom: 1px solid var(--cc-line);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    .cc-topline-title {
        font-size: 1rem;
        white-space: nowrap;
    }

    .cc-pill {
        margin-left: auto;
        max-width: 58vw;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: .68rem;
        padding: .37rem .58rem;
        background: #fff;
    }

    /* Hero becomes a compact service-firm card instead of a desktop billboard. */
    .cc-hero {
        grid-template-columns: 1fr;
        min-height: 0;
        border-radius: var(--cc-mobile-radius);
        margin-bottom: .72rem;
        box-shadow: var(--cc-mobile-shadow);
    }

    .cc-hero-copy {
        padding: 1.35rem 1.18rem 1.18rem;
    }

    .cc-kicker {
        font-size: .58rem;
        letter-spacing: .24em;
    }

    .cc-hero h1 {
        margin: .32rem 0 .25rem;
        font-size: clamp(2.05rem, 10.5vw, 3rem);
        line-height: .98;
    }

    .cc-hero-sub {
        font-size: 1.03rem;
        margin-top: .35rem;
    }

    .cc-hero-body {
        font-size: .82rem;
        line-height: 1.52;
    }

    .cc-hero-art {
        min-height: 72px;
        border-top: 1px solid rgba(214, 207, 196, .55);
        background:
            linear-gradient(90deg,rgba(255,255,255,.2),rgba(255,255,255,.58)),
            linear-gradient(115deg,#e8e0d4 0 22%,#faf8f3 22% 45%,#d7d1c6 45% 60%,#f6f3ed 60% 100%);
    }

    .cc-hero-art:after {
        top: .85rem;
        right: .9rem;
        width: 9.5rem;
        font-size: .49rem;
        line-height: 1.65;
        letter-spacing: .14em;
    }

    /* Four desktop KPIs become a clean 2x2 mobile summary. */
    .cc-grid-4 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .55rem;
        margin: .55rem 0 .72rem;
    }

    .cc-stat {
        min-height: 88px;
        border-radius: var(--cc-mobile-radius);
        padding: .78rem .72rem;
        box-shadow: var(--cc-mobile-shadow);
    }

    .cc-stat-row {
        gap: .55rem;
        align-items: flex-start;
    }

    .cc-stat-icon {
        width: 34px;
        height: 34px;
        flex: 0 0 34px;
        font-size: .95rem;
    }

    .cc-stat-value {
        font-size: 1.33rem;
        line-height: 1.05;
        overflow-wrap: anywhere;
    }

    .cc-stat-label {
        font-size: .66rem;
        line-height: 1.3;
    }

    .cc-panel {
        border-radius: var(--cc-mobile-radius);
        padding: .88rem .85rem;
        margin: .58rem 0;
        box-shadow: var(--cc-mobile-shadow);
    }

    .cc-panel-title {
        font-size: 1.02rem;
        margin-bottom: .55rem;
    }

    /* Progress is swipeable and keeps every stage readable. */
    .cc-stage-wrap {
        margin: 0 -.25rem;
        padding: .5rem .25rem .25rem;
        overflow-x: auto;
        overflow-y: hidden;
        scroll-snap-type: x proximity;
        scrollbar-width: none;
        justify-content: flex-start;
        -webkit-overflow-scrolling: touch;
    }

    .cc-stage-wrap::-webkit-scrollbar { display: none; }

    .cc-stage {
        min-width: 104px;
        flex: 0 0 104px;
        scroll-snap-align: start;
    }

    .cc-stage:not(:last-child):after {
        left: 61%;
        width: 78%;
    }

    .cc-stage-name {
        font-size: .66rem;
        line-height: 1.25;
    }

    .cc-stage-status {
        font-size: .58rem;
    }

    .cc-list-row {
        grid-template-columns: 30px minmax(0,1fr);
        gap: .58rem;
        padding: .72rem .05rem;
    }

    .cc-list-row > .cc-status {
        grid-column: 2;
        justify-self: start;
        margin-top: -.2rem;
    }

    .cc-list-title {
        font-size: .78rem;
        overflow-wrap: anywhere;
    }

    .cc-list-sub {
        font-size: .66rem;
    }

    .cc-owner-banner {
        border-radius: var(--cc-mobile-radius);
        padding: .9rem .95rem;
        align-items: flex-start;
        flex-direction: column;
        gap: .65rem;
    }

    .cc-owner-banner .cc-pill {
        margin-left: 0;
        max-width: none;
        background: rgba(255,255,255,.08);
        color: #f5f1e9;
        border-color: rgba(255,255,255,.18);
    }

    /* Native Streamlit components: touch-friendly and no squeezed desktop UI. */
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 46px;
        border-radius: 10px !important;
        width: 100%;
    }

    [data-testid="stMetric"] {
        border-radius: var(--cc-mobile-radius);
        padding: .8rem .82rem;
    }

    [data-testid="stDataFrame"] {
        border-radius: var(--cc-mobile-radius);
        overflow-x: auto;
        max-width: calc(100vw - (var(--cc-mobile-gutter) * 2));
    }

    div[data-testid="stExpander"] {
        border-radius: var(--cc-mobile-radius);
    }

    div[data-testid="stTabs"] [role="tablist"] {
        overflow-x: auto;
        scrollbar-width: none;
        flex-wrap: nowrap;
    }

    div[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display:none; }

    div[data-testid="stTabs"] button[role="tab"] {
        min-width: max-content;
        padding-left: .75rem;
        padding-right: .75rem;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: .6rem !important;
    }

    .stSelectbox, .stTextInput, .stTextArea, .stFileUploader {
        max-width: 100%;
    }

    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {
        border-radius: 10px;
    }

    [data-testid="stFileUploaderDropzone"] {
        border-radius: var(--cc-mobile-radius);
        padding: 1rem .8rem;
    }

    /* Remove desktop-like visual noise on small screens. */
    h1 { font-size: 2rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.18rem !important; }
    p, li { line-height: 1.48; }
}

@media (max-width: 430px) {
    :root { --cc-mobile-gutter: .68rem; }

    .cc-grid-4 { gap: .45rem; }
    .cc-stat { padding: .7rem .62rem; min-height: 82px; }
    .cc-stat-icon { width: 30px; height: 30px; flex-basis: 30px; font-size: .82rem; }
    .cc-stat-value { font-size: 1.2rem; }
    .cc-stat-label { font-size: .62rem; }
    .cc-hero-copy { padding: 1.2rem 1rem 1rem; }
    .cc-hero h1 { font-size: 2.15rem; }
    .cc-hero-art { min-height: 62px; }
    .cc-hero-art:after { width: 8.7rem; font-size: .45rem; }
    .cc-pill { max-width: 54vw; }
}

@media (max-width: 355px) {
    .cc-grid-4 { grid-template-columns: 1fr; }
    .cc-pill { max-width: 50vw; }
}
</style>
"""


def patch_mobile_theme(experience_shell) -> None:
    """Layer mobile presentation onto the role-aware portal without changing permissions.

    The wrapper runs inside experience_shell.run() immediately after page config, so
    the responsive CSS is present even when authentication later stops rendering.
    """

    original_theme = experience_shell._apply_brand_theme

    def responsive_theme() -> None:
        original_theme()
        st.markdown(MOBILE_CSS, unsafe_allow_html=True)

    experience_shell._apply_brand_theme = responsive_theme

    # 'auto' keeps the desktop rail available while allowing Streamlit to use its
    # native collapsed/drawer behavior on narrow screens.
    original_page_config = experience_shell.st.set_page_config

    def responsive_page_config(*args, **kwargs):
        kwargs["initial_sidebar_state"] = "auto"
        return original_page_config(*args, **kwargs)

    experience_shell.st.set_page_config = responsive_page_config
