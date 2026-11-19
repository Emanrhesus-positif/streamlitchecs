"""Les chiffres viennent de l'API FastAPI, pas des CSV.

Démarrer l'API dans un autre terminal :
    python -m uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from ui import PLOTLY_CONFIG, apply_theme, style_fig

if os.environ.get("AWP_UNIFIED") != "1":
    st.set_page_config(page_title="AWP — API", layout="wide", initial_sidebar_state="expanded")

apply_theme()

API_DEFAUT = os.environ.get("AWP_API_URL", "http://127.0.0.1:8000")
COMMANDE_API = (
    "python -m uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000"
)

st.title("Mon appli lit l'API, plus les CSV")
st.caption("Les ouvertures, les parties et la probabilité de victoire viennent du service FastAPI.")

with st.sidebar:
    st.header("API")
    api = st.text_input("URL de l'API", value=API_DEFAUT, key="api_base_url").rstrip("/")


def api_get(chemin: str, **params):
    reponse = requests.get(f"{api}{chemin}", params=params, timeout=8)
    reponse.raise_for_status()
    return reponse.json()


def verifier_api() -> tuple[bool, str]:
    try:
        api_get("/ouvertures", min_n=1)
        return True, ""
    except requests.RequestException as exc:
        return False, str(exc)


en_ligne, erreur = verifier_api()
if not en_ligne:
    st.error(
        "L'API ne répond pas. Lancez-la dans un autre terminal :\n\n"
        f"```powershell\n{COMMANDE_API}\n```\n\n"
        f"Détail : {erreur}"
    )
else:
    st.success(f"API joignable — {api}")

onglet1, onglet2 = st.tabs(["Ouvertures & parties", "Et si je change de conditions ?"])

# ---------------------------------------------------------------------------
# Onglet 1 : GET /ouvertures + GET /parties
# ---------------------------------------------------------------------------
with onglet1:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        cadence = st.selectbox(
            "Cadence",
            options=["(toutes)", "bullet", "blitz", "rapid"],
            key="exo5_cadence",
        )
    with c2:
        min_n = st.slider(
            "Parties minimum par ouverture",
            min_value=1,
            max_value=100,
            value=30,
            step=1,
            key="exo5_min_n",
        )
    with c3:
        limite = st.slider(
            "Nombre de parties récentes",
            min_value=5,
            max_value=100,
            value=10,
            step=5,
            key="exo5_limite",
        )

    params_ouvertures = {"min_n": min_n}
    params_parties = {"limit": limite}
    if cadence != "(toutes)":
        params_ouvertures["cadence"] = cadence
        params_parties["cadence"] = cadence

    if not en_ligne:
        st.info("Démarrez l'API puis rechargez cette page.")
    else:
        try:
            ouv = pd.DataFrame(api_get("/ouvertures", **params_ouvertures))
            parties = pd.DataFrame(api_get("/parties", **params_parties))
        except requests.RequestException as exc:
            st.error(f"Lecture impossible : {exc}")
        else:
            st.subheader("Ouvertures qui coûtent des points")
            if ouv.empty:
                st.info("Aucune famille avec ce minimum de parties. Baissez le curseur.")
            else:
                ouv_disp = ouv.iloc[::-1].reset_index(drop=True)
                fig = px.bar(
                    ouv_disp,
                    x="score",
                    y="famille",
                    orientation="h",
                    color="score",
                    color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
                    range_color=(0, 1),
                    text=ouv_disp["score"].map(lambda v: f"{v:.2f}"),
                    hover_data={"n": True, "gaffes": ":.2f", "score": ":.3f"},
                    title=f"Score moyen par famille (≥ {min_n} parties)",
                    labels={
                        "score": "Score moyen",
                        "famille": "Famille",
                        "n": "Parties",
                        "gaffes": "Gaffes / partie",
                    },
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(coloraxis_showscale=False)
                fig = style_fig(fig, height=430)
                fig.update_layout(margin=dict(l=165, r=35, t=60, b=20))
                st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

            st.subheader("Dernières parties")
            if parties.empty:
                st.info("Aucune partie pour ces filtres.")
            else:
                if "date_jeu" in parties:
                    parties["date_jeu"] = pd.to_datetime(parties["date_jeu"]).dt.strftime("%Y-%m-%d")
                if "couleur" in parties:
                    parties["couleur"] = (
                        parties["couleur"].map({"white": "Blancs", "black": "Noirs"}).fillna(parties["couleur"])
                    )
                st.dataframe(
                    parties,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "score": st.column_config.NumberColumn("score", format="%.2f"),
                        "ecart_elo": st.column_config.NumberColumn("écart Elo", format="%+d"),
                    },
                )

# ---------------------------------------------------------------------------
# Onglet 2 : POST /predict
# ---------------------------------------------------------------------------
with onglet2:
    with st.form("form_predict"):
        a, b = st.columns(2)
        with a:
            couleur = st.selectbox(
                "Couleur",
                options=["white", "black"],
                format_func=lambda x: "Blancs" if x == "white" else "Noirs",
                key="pred_couleur",
            )
            cadence_pred = st.selectbox(
                "Cadence",
                options=["bullet", "blitz", "rapid", "classical", "aucune"],
                key="pred_cadence",
            )
        with b:
            ecart_elo = st.number_input(
                "Écart d'Elo (adversaire − moi)",
                value=0.0,
                step=10.0,
                format="%.1f",
                key="pred_ecart_elo",
            )
            heure = st.slider("Heure UTC", min_value=0, max_value=23, value=20, key="pred_heure")
        envoyer = st.form_submit_button("Estimer ma probabilité de victoire")

    if envoyer:
        charge = {
            "couleur": couleur,
            "cadence": cadence_pred,
            "ecart_elo": float(ecart_elo),
            "heure": int(heure),
        }
        try:
            reponse = requests.post(f"{api}/predict", json=charge, timeout=8)
        except requests.RequestException as exc:
            st.error(f"API injoignable : {exc}")
        else:
            if reponse.status_code == 422:
                st.error(f"Paramètres refusés par l'API (422) : {reponse.text}")
            elif not reponse.ok:
                st.error(f"Erreur API ({reponse.status_code}) : {reponse.text}")
            else:
                proba = reponse.json().get("proba_victoire")
                if proba is None:
                    st.warning("Le modèle n'est pas chargé côté API.")
                else:
                    st.metric("Probabilité de victoire estimée", f"{100 * proba:.1f} %")
                    st.caption(
                        f"{'Blancs' if couleur == 'white' else 'Noirs'} · {cadence_pred} · "
                        f"écart Elo {ecart_elo:+.0f} · {heure} h UTC"
                    )
