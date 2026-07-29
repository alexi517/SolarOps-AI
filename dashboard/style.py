"""Centralised CSS and small shared layout helpers (polish pass,
docs/hase7b-dashboard-polish-pass.md §2-3). Presentation only — no api calls,
no business logic; every page still gets its data through api_client.py."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

import config
import streamlit as st

__all__ = [
    "inject_global_css",
    "header",
    "pill",
    "card",
    "risk_pill_kind",
    "severity_pill_kind",
    "status_pill_kind",
    "apply_chart_theme",
    "apply_gauge_theme",
]

_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
#MainMenu, footer { visibility: hidden; }

.solarops-header-strip {
    height: 6px;
    border-radius: 6px;
    margin-bottom: 1.25rem;
    background: linear-gradient(90deg, #4CAF50 0%, #A5D6A7 100%);
}

/* Any st.container(key="card-...") becomes a rounded white card. */
div[class*="st-key-card-"] {
    background: #FFFFFF;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    padding: 20px;
    margin-bottom: 16px;
}

/* Metric tiles: the label above each value reads as a small pill/badge
   (same chip language as the status pills elsewhere), not plain text. The
   pill styling is put on the labelled container itself and forced onto
   every descendant, rather than a guessed p/span child — Streamlit renders
   the label's inner markup as whatever tag its version emits, so targeting
   only specific child tags is fragile across versions. */
div[data-testid="stMetricLabel"] {
    display: inline-flex !important;
    align-items: center;
    width: fit-content;
    background: #E3F3E4 !important;
    padding: 3px 12px !important;
    border-radius: 999px !important;
}
div[data-testid="stMetricLabel"] * {
    color: #256029 !important;
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    background: transparent !important;
}
div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] div {
    font-size: 1.4rem !important;
}

.pill {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.pill-green { background: #E3F3E4; color: #256029; }
.pill-amber { background: #FFF3D6; color: #7A5B00; }
.pill-red   { background: #FBE3E1; color: #8A2A22; }

.stButton > button { border-radius: 10px; }

/* Any st.container(key="danger-...") turns its button red (Reject etc). */
div[class*="st-key-danger-"] button {
    background-color: #E5453F;
    color: #FFFFFF;
    border: 1px solid #E5453F;
}
div[class*="st-key-danger-"] button:hover {
    background-color: #C43A34;
    border-color: #C43A34;
    color: #FFFFFF;
}

/* --- Sidebar nav: soft green ground, spacious pill-style links (matches
   the product's own UI spec — see dashboard/README.md). Streamlit's sidebar
   nav has no CSS classes to hook (styles are emotion-generated at runtime),
   so these target the stable data-testid attributes its React components
   render; !important is needed to beat Streamlit's own scoped styles. --- */
section[data-testid="stSidebar"] {
    background-color: #EFF6EF;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.5rem;
}

.side-brand {
    display: flex;
    align-items: center;
    font-family: inherit;
    font-size: 1.15rem;
    font-weight: 700;
    color: #1C2B24;
    padding: 0 0.9rem 1.25rem;
}

[data-testid="stNavSectionHeader"] {
    font-size: 0.7rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #5B6B62 !important;
    font-weight: 600 !important;
    padding: 0.5rem 0.9rem 0.4rem !important;
}

[data-testid="stSidebarNavItems"] {
    gap: 0.2rem;
    padding: 0 0.4rem;
}

[data-testid="stSidebarNavLinkContainer"] {
    margin-bottom: 0.2rem;
}

[data-testid="stSidebarNavLink"] {
    border-radius: 12px !important;
    padding: 0.65rem 0.9rem !important;
    font-size: 0.95rem !important;
    color: #1C2B24 !important;
    gap: 0.65rem;
    transition: background-color 120ms ease;
}
[data-testid="stSidebarNavLink"]:hover {
    background-color: rgba(255, 255, 255, 0.6) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #FFFFFF !important;
    box-shadow: 0 2px 10px rgba(28, 43, 36, 0.08);
    font-weight: 600 !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"]:hover {
    background-color: #FFFFFF !important;
}
</style>
"""


def inject_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def header(title: str, icon: str = "") -> None:
    """Header row every page opens with: title (left), site selector + a
    last-updated caption (right). Only one site exists today (SystemComposition
    wires a single site) — the selector reflects that honestly rather than
    listing sites that don't exist."""
    st.markdown('<div class="solarops-header-strip"></div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2])
    with left:
        st.title(f"{icon}  {title}".strip())
    with right:
        st.selectbox(
            "Site",
            [config.SITE_ID],
            disabled=True,
            key=f"site-selector-{title}",
            help="Only one site is wired up today.",
        )
        st.caption(f"Page loaded {datetime.now():%H:%M}")


def pill(text: str, kind: str) -> str:
    """kind: 'green' | 'amber' | 'red'. Returns raw HTML for the caller to
    st.markdown(..., unsafe_allow_html=True)."""
    return f'<span class="pill pill-{kind}">{text}</span>'


@contextmanager
def card(key: str) -> Iterator[None]:
    with st.container(key=f"card-{key}"):
        yield


def risk_pill_kind(level: str) -> str:
    return {"LOW": "green", "MEDIUM": "amber", "HIGH": "red", "CRITICAL": "red"}.get(
        level, "amber"
    )


def severity_pill_kind(severity: str) -> str:
    return {"INFO": "green", "WARNING": "amber", "CRITICAL": "red"}.get(severity, "amber")


def status_pill_kind(status: str) -> str:
    if status in ("COMPLETED", "VERIFIED", "AUTO_APPROVED", "APPROVED"):
        return "green"
    if status in (
        "REJECTED_BY_OPERATOR",
        "REJECTED_BY_POLICY",
        "REJECTED_BY_RISK",
        "BLOCKED_BY_SAFETY",
        "DISPATCH_FAILED",
        "EXECUTION_FAILED",
        "VERIFICATION_FAILED",
        "TIMED_OUT",
        "CANCELLED",
    ):
        return "red"
    return "amber"


def apply_chart_theme(fig, *, height: int = 300, show_legend: bool = False):
    """Common styling for axis-based Plotly charts (line/area — not gauges).

    ``automargin=True`` is the actual fix for tick labels getting clipped at
    the card edge: a fixed pixel margin only fits whatever tick text you
    guessed at design time, and real data (e.g. a 3-digit kW reading) can be
    wider — automargin tells Plotly to expand as needed instead of cutting
    text off.

    The legend sits *below* the plot, not above it — legend at y > 1 shares
    the same corner as the title and crowds it; anchored under the axis
    instead, with a top margin so the title itself has breathing room.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin={"l": 10, "r": 20, "t": 46, "b": 64 if show_legend else 40},
        font={"family": "sans-serif", "color": "#1C2B24", "size": 13},
        title={"font": {"size": 14, "color": "#1C2B24"}},
        showlegend=show_legend,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.28,
            "x": 0.5,
            "xanchor": "center",
        },
        hoverlabel={"bgcolor": "white", "font_size": 12, "font_family": "sans-serif"},
    )
    fig.update_xaxes(showgrid=False, automargin=True, tickfont={"size": 12})
    fig.update_yaxes(
        showgrid=True, gridcolor="rgba(0,0,0,0.06)", automargin=True, tickfont={"size": 12}
    )
    return fig


def apply_gauge_theme(fig, *, height: int = 260):
    """Common styling for Plotly Indicator gauges — no cartesian axes, so no
    automargin needed, just consistent transparent background/font/sizing."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin={"l": 30, "r": 30, "t": 40, "b": 20},
        font={"family": "sans-serif", "color": "#1C2B24"},
    )
    return fig
