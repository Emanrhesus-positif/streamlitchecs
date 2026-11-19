"""Exo 5, suite : l'appli ne lit plus les CSV, elle demande à l'API. Environ 45 min.

Question : la même appli qu'à l'exo 2, mais ses chiffres viennent de l'API.
À produire : une barre latérale (cadence, parties minimum), la figure des familles depuis GET /ouvertures,
les dix dernières parties depuis GET /parties, et un message lisible si l'API ne répond pas.
Vous pouvez aussi modifier directement votre app_streamlit.py ou votre app_dash.py.
Lancez api.py d'abord.
Lancer : uv run streamlit run fil_rouge/app_api.py --server.address 127.0.0.1
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from single_instance import bootstrap_streamlit_app

bootstrap_streamlit_app(__file__, port=8503)

import os as _os  # noqa: F401 (keep compatibility)

# (re-import os names already available)

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API = os.environ.get("AWP_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Mes parties d'échecs", layout="wide")
st.title("Quelles ouvertures me coûtent des points\u00a0?")


def appeler(chemin: str, **params) -> pd.DataFrame:
    """Appelle l'API et renvoie un DataFrame (lève une erreur lisible si problème)."""
    r = requests.get(f"{API}{chemin}", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data)


# Barre latérale : cadence (blitz, rapid, bullet) et parties minimum par ouverture
with st.sidebar:
    st.header("Paramètres")
    cadence = st.selectbox("Cadence", options=["(toutes)", "blitz", "rapid", "bullet"], key="api_cadence")
    min_n = st.slider("Parties minimum par ouverture", min_value=1, max_value=100, value=30, step=1, key="api_min_n")

params_ouv = {"min_n": min_n}
if cadence != "(toutes)":
    params_ouv["cadence"] = cadence

try:
    ouv = appeler("/ouvertures", **params_ouv)
except requests.RequestException as e:
    st.error(
        "Impossible de joindre l'API. Lancez d'abord le service : "
        "`uv run uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000 --reload`\n\n"
        f"Détail : {e}"
    )
    st.stop()

# Figure des familles (barres horizontales, la pire en haut)
st.subheader("Familles d'ouvertures (données issues de l'API)")
if ouv.empty:
    st.info("Aucune famille ne correspond aux critères (essayez de baisser le minimum de parties).")
else:
    ouv_disp = ouv.sort_values("score", ascending=False).reset_index(drop=True)  # pire en haut
    fig = px.bar(
        ouv_disp,
        x="score",
        y="famille",
        orientation="h",
        title="Score moyen par famille d'ouvertures (la pire en haut)",
        labels={
            "score": "Score moyen (1 = victoire, 0 = défaite)",
            "famille": "Famille d'ouverture",
            "n": "Parties",
            "gaffes": "Gaffes / partie",
        },
        hover_data=[c for c in ["n", "gaffes"] if c in ouv_disp.columns],
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, width="stretch")

# Dix dernières parties depuis GET /parties
st.subheader("Dix dernières parties")
params_parties = {"limit": 10}
if cadence != "(toutes)":
    params_parties["cadence"] = cadence

try:
    parties = appeler("/parties", **params_parties)
except requests.RequestException as e:
    st.error(f"Impossible de récupérer les parties depuis l'API : {e}")
    st.stop()

if parties.empty:
    st.info("Aucune partie trouvée pour ces critères.")
else:
    st.dataframe(parties, width="stretch", hide_index=True)
