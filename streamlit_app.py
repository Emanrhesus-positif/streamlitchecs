"""Point d'entrée Streamlit Community Cloud.

Streamlit Cloud propose ``streamlit_app.py`` à la racine du dépôt. Ce fichier
reprend exactement la navigation de ``fil_rouge/app.py``, avec des chemins
relatifs à la racine. En local, ``python -m streamlit run fil_rouge/app.py``
fonctionne aussi.
"""

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "fil_rouge"))

os.environ["AWP_UNIFIED"] = "1"

import streamlit as st  # noqa: E402

from single_instance import bootstrap_streamlit_app  # noqa: E402

bootstrap_streamlit_app(__file__, port=8501)

st.set_page_config(
    page_title="AWP — Échecs",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("fil_rouge/01_figures.py", title="Analyse — où je perds des points", icon="♟️", default=True),
    st.Page("fil_rouge/pages/02_Exo2_Appli_hebdo.py", title="Appli hebdo — filtres & figures", icon="📊"),
    st.Page("fil_rouge/pages/04_Exo4_Dash_drilldown.py", title="Drill-down — ouvertures → coups", icon="🔎"),
    st.Page("fil_rouge/pages/05_Exo5_API_et_clients.py", title="API & modèle — clients", icon="🔌"),
    st.Page("fil_rouge/pages/06_Exo6_MCP_et_outils.py", title="Outils MCP — console", icon="🤖"),
]

navigation = st.navigation(pages, position="sidebar")
navigation.run()
