from __future__ import annotations

import streamlit as st


LUXURY_MOBILE_OVERRIDE_CSS = r"""
<style>
@media (max-width: 820px) {
    :root {
        --cc-mobile-radius: 6px;
        --cc-mobile-shadow: 0 10px 28px rgba(28, 26, 22, .05);
    }

    [data-testid="stHeader"],
    .cc-topline {
        background: rgba(246, 243, 237, .965) !important;
        border-bottom-color: #dcd5ca !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(242, 238, 231, .99) !important;
        box-shadow: 14px 0 38px rgba(28, 26, 22, .10) !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label,
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    .stButton > button,
    .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {
        border-radius: 4px !important;
    }

    .cc-hero {
        border-radius: 3px !important;
        border-color: #c9c0b3 !important;
    }

    .cc-hero-art {
        background:
            linear-gradient(155deg, rgba(255,255,255,.76), rgba(255,255,255,.08)),
            repeating-linear-gradient(90deg, transparent 0 30px, rgba(148,112,59,.04) 30px 31px),
            #e9e2d7 !important;
    }

    .cc-stat,
    .cc-panel,
    [data-testid="stMetric"],
    [data-testid="stDataFrame"],
    div[data-testid="stExpander"],
    [data-testid="stFileUploaderDropzone"] {
        border-radius: 5px !important;
        box-shadow: var(--cc-mobile-shadow) !important;
    }

    .cc-owner-banner {
        border-radius: 3px !important;
    }

    .cc-pill,
    .cc-status {
        box-shadow: none !important;
    }
}
</style>
"""


def apply_luxury_mobile_overrides() -> None:
    st.markdown(LUXURY_MOBILE_OVERRIDE_CSS, unsafe_allow_html=True)
