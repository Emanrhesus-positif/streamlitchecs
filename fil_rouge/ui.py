"""Thème sombre commun à toutes les pages Streamlit du fil rouge.

Le thème natif est aussi réglé dans `.streamlit/config.toml` ; ce module ajoute
les finitions « glass » (barre latérale, cartes, boutons, tableaux, menus).
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

PRIMARY = "#7c9cff"
TEXT = "#e5e7eb"
MUTED = "#9aa4b2"
PANEL = "rgba(255, 255, 255, 0.055)"
BORDER = "rgba(255, 255, 255, 0.13)"
GOOD = "#22c55e"
WARN = "#f59e0b"
BAD = "#ef4444"

CSS = """
<style>
:root {
  --awp-bg: #05070d;
  --awp-panel: rgba(255, 255, 255, 0.055);
  --awp-border: rgba(255, 255, 255, 0.13);
  --awp-text: #e5e7eb;
  --awp-muted: #9aa4b2;
  --awp-primary: #7c9cff;
}

.stApp,
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 12% 0%, #141d33 0%, #080b14 42%, #03040a 100%) !important;
  color: var(--awp-text);
}
[data-testid="stHeader"] {
  background: rgba(0, 0, 0, 0) !important;
}
.block-container {
  padding-top: 1.6rem;
  padding-bottom: 3rem;
  max-width: 1320px;
}

h1, h2, h3, h4, h5, h6 {
  color: #f8fafc !important;
  letter-spacing: -0.01em;
}
p, span, label, li, .stMarkdown, .stCaption, [data-testid="stCaptionContainer"] {
  color: var(--awp-text);
}
small, .stCaption, [data-testid="stCaptionContainer"] p {
  color: var(--awp-muted) !important;
}
a { color: #93b4ff !important; }

/* ----- Barre latérale ----- */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
  background: linear-gradient(180deg, #0d1424 0%, #070a12 100%) !important;
  color: var(--awp-text) !important;
  border-right: 1px solid var(--awp-border);
}
[data-testid="stSidebarHeader"] { background: transparent !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: var(--awp-text) !important; }
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] span {
  color: #cbd5e1 !important;
  border-radius: 10px;
}
[data-testid="stSidebarNav"] a:hover {
  background: rgba(124, 156, 255, 0.14) !important;
  color: #ffffff !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background: rgba(124, 156, 255, 0.20) !important;
  color: #ffffff !important;
  font-weight: 600;
}

/* ----- Cartes / métriques ----- */
div[data-testid="stMetric"] {
  background: var(--awp-panel);
  border: 1px solid var(--awp-border);
  border-radius: 16px;
  padding: 14px 18px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
}
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricValue"] div,
div[data-testid="stMetricDelta"] div { color: #f8fafc !important; }
div[data-testid="stMetricLabel"] p { color: var(--awp-muted) !important; }

/* ----- Boutons ----- */
.stButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button {
  background: rgba(255, 255, 255, 0.075) !important;
  color: #f8fafc !important;
  border: 1px solid rgba(255, 255, 255, 0.22) !important;
  border-radius: 13px !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32);
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
  min-height: 2.5rem;
}
.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stFormSubmitButton"] > button:hover {
  background: rgba(124, 156, 255, 0.20) !important;
  border-color: rgba(148, 176, 255, 0.60) !important;
  transform: translateY(-1px);
}
.stButton > button:disabled {
  opacity: 0.42;
  transform: none;
}

/* ----- Champs / sélecteurs ----- */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
.stTextInput input,
.stNumberInput input,
.stDateInput input {
  background: rgba(255, 255, 255, 0.065) !important;
  color: #f3f4f6 !important;
  border-color: var(--awp-border) !important;
  border-radius: 11px !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] input,
[data-baseweb="input"] input { color: #f3f4f6 !important; }
[data-baseweb="select"] svg { color: #cbd5e1 !important; }

/* Menus déroulants : rendus dans un portail hors du conteneur principal */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-baseweb="menu"] {
  background: #111827 !important;
  border: 1px solid var(--awp-border) !important;
  color: #f3f4f6 !important;
}
ul[data-baseweb="menu"] li,
div[role="option"] {
  background: transparent !important;
  color: #e5e7eb !important;
}
ul[data-baseweb="menu"] li:hover,
div[role="option"]:hover,
div[aria-selected="true"] {
  background: rgba(124, 156, 255, 0.22) !important;
  color: #ffffff !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
  background: rgba(124, 156, 255, 0.24) !important;
  color: #eef2ff !important;
}

/* ----- Onglets ----- */
[data-baseweb="tab-list"] {
  gap: 4px;
  border-bottom: 1px solid var(--awp-border);
}
[data-baseweb="tab"] {
  color: #b7c0cf !important;
  background: transparent !important;
}
[data-baseweb="tab"][aria-selected="true"] {
  color: #ffffff !important;
  border-bottom-color: var(--awp-primary) !important;
}
[data-baseweb="tab-highlight"] { background: var(--awp-primary) !important; }

/* ----- Alertes, expanders, code, tableaux ----- */
div[data-testid="stAlert"] {
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid var(--awp-border);
  color: var(--awp-text);
  border-radius: 13px;
}
div[data-testid="stAlert"] p { color: var(--awp-text) !important; }
details, [data-testid="stExpander"] {
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--awp-border);
  border-radius: 13px;
}
details summary, [data-testid="stExpander"] summary { color: #e5e7eb !important; }
pre, code, .stCode, [data-testid="stCode"] {
  background: #0b1220 !important;
  color: #e5e7eb !important;
}
div[data-testid="stDataFrame"],
div[data-testid="stDataFrameResizable"] {
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--awp-border);
  border-radius: 12px;
}
[data-testid="stTable"] table { color: var(--awp-text); }

/* ----- Sliders, toggles, progression, divers ----- */
[data-testid="stSlider"] [role="slider"] { background: var(--awp-primary) !important; }
[data-testid="stSlider"] div[data-baseweb="slider"] div { color: #cbd5e1; }
[data-testid="stProgress"] > div > div > div > div { background: var(--awp-primary); }
hr { border-color: var(--awp-border) !important; }
[data-testid="stDivider"] { border-color: var(--awp-border) !important; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #27324a; border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

/* Streamlit ajoute un fond blanc au conteneur des composants HTML */
iframe[title="streamlit_component"] { background: transparent !important; }
</style>
"""


def apply_theme() -> None:
    """Injecte le CSS commun (à appeler après st.set_page_config)."""
    st.markdown(CSS, unsafe_allow_html=True)


def style_fig(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    """Applique le thème sombre et des axes lisibles à une figure Plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11, 18, 32, 0.55)",
        font=dict(color=TEXT, family="Inter, Segoe UI, sans-serif"),
        title=dict(font=dict(color="#f8fafc", size=18), x=0.01),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
        margin=dict(l=10, r=18, t=64, b=18),
        hoverlabel=dict(bgcolor="#111827", bordercolor=BORDER, font=dict(color=TEXT)),
    )
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.075)",
        zerolinecolor="rgba(255,255,255,0.12)",
        tickfont=dict(color=TEXT),
        title_font=dict(color=TEXT),
        linecolor="rgba(255,255,255,0.18)",
    )
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.075)",
        zerolinecolor="rgba(255,255,255,0.12)",
        tickfont=dict(color=TEXT),
        title_font=dict(color=TEXT),
        linecolor="rgba(255,255,255,0.18)",
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
