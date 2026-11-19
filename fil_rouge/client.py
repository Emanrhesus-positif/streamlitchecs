"""Bonus de l'exo 5 : une appli Streamlit « et si ? » qui appelle POST /predict.

Question : et si je jouais plus tard, ou avec les noirs ?
À produire : un formulaire (couleur, cadence, écart d'Elo, heure), un requests.post vers /predict,
un st.metric, et un message lisible si l'API refuse la requête (422) ou ne répond pas.
Lancez api.py d'abord.
Lancer : uv run streamlit run fil_rouge/client.py --server.address 127.0.0.1
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from single_instance import bootstrap_streamlit_app

bootstrap_streamlit_app(__file__, port=8504)

import requests
import streamlit as st

API = os.environ.get("AWP_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Et si ? — Probabilité de victoire", layout="centered")
st.title("Et si je jouais plus tard, ou avec les noirs ?")
st.caption("Formulaire qui appelle POST /predict sur l’API (modèle fourni).")

with st.form("predict_form"):
    couleur = st.selectbox(
        "Couleur",
        options=["white", "black"],
        format_func=lambda x: "Blancs" if x == "white" else "Noirs",
        key="pred_couleur",
    )
    cadence = st.selectbox(
        "Cadence",
        options=["bullet", "blitz", "rapid", "classical", "aucune"],
        key="pred_cadence",
    )
    ecart_elo = st.number_input(
        "Écart d’Elo (Elo adverse − Elo joueur)",
        value=0.0,
        step=10.0,
        format="%.1f",
        key="pred_ecart_elo",
    )
    heure = st.slider("Heure de la partie (UTC)", min_value=0, max_value=23, value=20, key="pred_heure")
    submitted = st.form_submit_button("Estimer ma probabilité de victoire")

if submitted:
    payload = {
        "couleur": couleur,
        "cadence": cadence,
        "ecart_elo": float(ecart_elo),
        "heure": int(heure),
    }
    try:
        r = requests.post(f"{API}/predict", json=payload, timeout=10)
        if r.status_code == 422:
            # Erreur de validation : afficher le détail renvoyé par FastAPI
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            st.error(f"Requête refusée par l’API (422 — paramètres invalides). Détail : {detail}")
        elif not r.ok:
            st.error(f"L’API a renvoyé une erreur ({r.status_code}). Détail : {r.text}")
        else:
            data = r.json()
            proba = data.get("proba_victoire")
            if proba is None:
                st.warning("Le modèle n’est pas disponible côté API.")
            else:
                st.metric("Probabilité de victoire estimée", f"{proba * 100:.1f} %")
                st.caption(
                    f"Scénario : {('Blancs' if couleur == 'white' else 'Noirs')}, cadence {cadence}, "
                    f"écart Elo {ecart_elo:+.0f}, à {heure}h UTC."
                )
    except requests.RequestException as e:
        st.error(
            "Impossible de joindre l’API. Lancez d’abord le service : "
            "`uv run uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000 --reload`\n\n"
            f"Détail : {e}"
        )
