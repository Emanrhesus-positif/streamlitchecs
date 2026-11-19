"""Console des outils exposés au LLM par le serveur MCP.

Ces trois appels sont exactement ceux que ``mcp_server.py`` expose :
pire_ouvertures, dernieres_parties et proba_victoire. Ils passent par l'API
FastAPI quand elle tourne ; sinon, la page exécute le même code en local
(``serving.py``), pour rester utilisable sur Streamlit Community Cloud.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests
import streamlit as st

from serving import ouvertures_records, parties_records, predire_proba
from ui import apply_theme

if os.environ.get("AWP_UNIFIED") != "1":
    st.set_page_config(page_title="AWP — Outils MCP", layout="wide", initial_sidebar_state="expanded")

apply_theme()


def _api_defaut() -> str:
    if os.environ.get("AWP_API_URL"):
        return os.environ["AWP_API_URL"]
    try:
        return st.secrets["AWP_API_URL"]
    except Exception:
        return "http://127.0.0.1:8000"


API_DEFAUT = _api_defaut()
COMMANDE_API = "python -m uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000"
COMMANDE_MCP = "python fil_rouge/mcp_server.py"

st.title("Les outils que le LLM peut appeler")
st.caption(
    "Chaque outil est exposé par `mcp_server.py` et interroge l'API FastAPI. "
    "Quand l'API n'est pas joignable (déploiement Streamlit Cloud), la page exécute le même code en local."
)


@st.cache_data(ttl=15, show_spinner=False)
def api_disponible(url: str) -> bool:
    try:
        reponse = requests.get(f"{url}/ouvertures", params={"min_n": 1}, timeout=3)
        return reponse.ok
    except requests.RequestException:
        return False


with st.sidebar:
    st.header("API")
    api = st.text_input("URL de l'API", value=API_DEFAUT, key="mcp_api_url").rstrip("/")
    en_ligne = api_disponible(api)
    st.caption("API joignable" if en_ligne else "API non joignable : calcul intégré")
    if st.button("Revérifier l'API", key="mcp_recheck"):
        api_disponible.clear()
        st.rerun()

if en_ligne:
    st.success(f"API joignable — {api}")
else:
    st.info(
        "**API non déployée** : les outils s'exécutent dans l'app, avec les mêmes fonctions "
        "que l'API (`serving.py`). En local, lancez l'API pour passer par HTTP."
    )


def appeler_get(chemin: str, **params):
    r = requests.get(f"{api}{chemin}", params=params, timeout=8)
    r.raise_for_status()
    return r.json()


outil = st.radio(
    "Outil",
    options=["pire_ouvertures", "dernieres_parties", "proba_victoire"],
    horizontal=True,
    key="mcp_outil",
)

# ---------------------------------------------------------------------------
# pire_ouvertures
# ---------------------------------------------------------------------------
if outil == "pire_ouvertures":
    c1, c2 = st.columns(2)
    with c1:
        cadence = st.selectbox("Cadence", ["(toutes)", "bullet", "blitz", "rapid"], key="mcp_cadence")
    with c2:
        min_n = st.number_input("min_n", min_value=1, max_value=500, value=30, step=1, key="mcp_min_n")

    if st.button("Appeler pire_ouvertures", key="mcp_call_ouv"):
        cadence_param = None if cadence == "(toutes)" else cadence
        if en_ligne:
            params = {"min_n": int(min_n)}
            if cadence_param:
                params["cadence"] = cadence_param
            try:
                data = appeler_get("/ouvertures", **params)
            except requests.RequestException as exc:
                st.error(f"Échec : {exc}")
                st.stop()
        else:
            data = ouvertures_records(cadence_param, min_n=int(min_n))

        frame = pd.DataFrame(data)
        if frame.empty:
            st.info("Aucune famille avec ce seuil.")
        else:
            st.dataframe(
                frame.head(10),
                width="stretch",
                hide_index=True,
                column_config={
                    "score": st.column_config.NumberColumn("score", format="%.3f"),
                    "gaffes": st.column_config.NumberColumn("gaffes / partie", format="%.2f"),
                },
            )
            st.caption("Source : API FastAPI" if en_ligne else "Source : calcul intégré (même code que l'API)")

# ---------------------------------------------------------------------------
# dernieres_parties
# ---------------------------------------------------------------------------
elif outil == "dernieres_parties":
    c1, c2, c3 = st.columns(3)
    with c1:
        cadence = st.selectbox(
            "Cadence",
            ["(toutes)", "bullet", "blitz", "rapid", "classical", "aucune"],
            key="mcp_cadence2",
        )
    with c2:
        couleur = st.selectbox(
            "Couleur",
            ["(toutes)", "white", "black"],
            format_func=lambda x: {"(toutes)": "Toutes", "white": "Blancs", "black": "Noirs"}[x],
            key="mcp_couleur",
        )
    with c3:
        limite = st.number_input("limit", min_value=1, max_value=500, value=10, step=1, key="mcp_limit")

    if st.button("Appeler dernieres_parties", key="mcp_call_parties"):
        cadence_param = None if cadence == "(toutes)" else cadence
        couleur_param = None if couleur == "(toutes)" else couleur
        if en_ligne:
            params = {"limit": int(limite)}
            if cadence_param:
                params["cadence"] = cadence_param
            if couleur_param:
                params["couleur"] = couleur_param
            try:
                data = appeler_get("/parties", **params)
            except requests.RequestException as exc:
                st.error(f"Échec : {exc}")
                st.stop()
        else:
            data = parties_records(cadence_param, couleur_param, limit=int(limite))

        frame = pd.DataFrame(data)
        if frame.empty:
            st.info("Aucune partie.")
        else:
            if "date_jeu" in frame:
                frame["date_jeu"] = pd.to_datetime(frame["date_jeu"]).dt.strftime("%Y-%m-%d")
            if "couleur" in frame:
                frame["couleur"] = frame["couleur"].map({"white": "Blancs", "black": "Noirs"}).fillna(frame["couleur"])
            st.dataframe(frame, width="stretch", hide_index=True)
            st.caption("Source : API FastAPI" if en_ligne else "Source : calcul intégré (même code que l'API)")

# ---------------------------------------------------------------------------
# proba_victoire
# ---------------------------------------------------------------------------
else:
    with st.form("mcp_predict"):
        a, b = st.columns(2)
        with a:
            couleur = st.selectbox(
                "Couleur",
                ["white", "black"],
                format_func=lambda x: "Blancs" if x == "white" else "Noirs",
                key="mcp_pred_couleur",
            )
            cadence = st.selectbox(
                "Cadence",
                ["bullet", "blitz", "rapid", "classical", "aucune"],
                key="mcp_pred_cadence",
            )
        with b:
            ecart = st.number_input("Écart d'Elo (adversaire − moi)", value=0.0, step=10.0, key="mcp_pred_ecart")
            heure = st.slider("Heure UTC", 0, 23, 20, key="mcp_pred_heure")
        envoyer = st.form_submit_button("Appeler proba_victoire")

    if envoyer:
        proba = None
        if en_ligne:
            charge = {
                "couleur": couleur,
                "cadence": cadence,
                "ecart_elo": float(ecart),
                "heure": int(heure),
            }
            try:
                reponse = requests.post(f"{api}/predict", json=charge, timeout=8)
            except requests.RequestException as exc:
                st.error(f"Échec : {exc}")
            else:
                if reponse.status_code == 422:
                    st.error(f"Paramètres refusés (422) : {reponse.text}")
                elif not reponse.ok:
                    st.error(f"Erreur API ({reponse.status_code}) : {reponse.text}")
                else:
                    proba = reponse.json().get("proba_victoire")
        else:
            proba = predire_proba(couleur, cadence, float(ecart), int(heure))

        if proba is None:
            st.warning("Modèle indisponible.")
        else:
            st.metric("Probabilité de victoire", f"{100 * proba:.1f} %")
            st.caption("Source : API FastAPI" if en_ligne else "Source : calcul intégré (même code que l'API)")

with st.expander("Lancer le serveur MCP", expanded=False):
    st.code(
        f"# 1. API\n{COMMANDE_API}\n\n"
        f"# 2. Serveur MCP (stdio : il attend un client)\n{COMMANDE_MCP}\n\n"
        "# 3. Client MCP, exemple avec Claude Code\n"
        "claude mcp add --transport stdio echecs -- python fil_rouge/mcp_server.py",
        language="powershell",
    )
