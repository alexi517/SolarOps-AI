"""Dashboard entry point — navigation only, no business logic (brief §0/§1).
Run with: streamlit run dashboard/app.py"""

from __future__ import annotations

import streamlit as st
import style
from pages import anomalies, approvals, commands, forecasts, overview, recommendations

st.set_page_config(page_title="SolarOps AI", page_icon="⚡", layout="wide")
style.inject_global_css()

st.sidebar.markdown(
    '<div class="side-brand">⚡&nbsp;&nbsp;SolarOps AI</div>', unsafe_allow_html=True
)

navigation = st.navigation(
    {
        "Screens": [
            st.Page(
                overview.render, title="Overview", icon="🏭", url_path="overview", default=True
            ),
            st.Page(forecasts.render, title="Forecasts", icon="📈", url_path="forecasts"),
            st.Page(anomalies.render, title="Anomalies", icon="⚠️", url_path="anomalies"),
            st.Page(
                recommendations.render,
                title="Recommendations",
                icon="🧠",
                url_path="recommendations",
            ),
            st.Page(approvals.render, title="Approvals", icon="✅", url_path="approvals"),
            st.Page(commands.render, title="Commands", icon="📋", url_path="commands"),
        ]
    }
)
navigation.run()
