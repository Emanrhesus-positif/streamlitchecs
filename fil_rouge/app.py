"""Serveur Streamlit unique : toutes les pages du fil rouge échecs.

Lancer :
    python -m streamlit run fil_rouge/app.py

Les pages :
  - Analyse : trois figures + simulateur des moments critiques
  - Appli hebdo : filtres, indicateurs, figures
  - Drill-down : ouvertures → parties → coups
  - API : client FastAPI + modèle /predict
  - Outils MCP : console des outils exposés au LLM
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from single_instance import bootstrap_streamlit_app

bootstrap_streamlit_app(__file__, port=8501)

import streamlit as st

os.environ["AWP_UNIFIED"] = "1"

st.set_page_config(
    page_title="AWP — Échecs",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("01_figures.py", title="Analyse — où je perds des points", icon="♟️", default=True),
    st.Page("pages/02_Exo2_Appli_hebdo.py", title="Appli hebdo — filtres & figures", icon="📊"),
    st.Page("pages/04_Exo4_Dash_drilldown.py", title="Drill-down — ouvertures → coups", icon="🔎"),
    st.Page("pages/05_Exo5_API_et_clients.py", title="API & modèle — clients", icon="🔌"),
    st.Page("pages/06_Exo6_MCP_et_outils.py", title="Outils MCP — console", icon="🤖"),
]

navigation = st.navigation(pages, position="sidebar")
navigation.run()
