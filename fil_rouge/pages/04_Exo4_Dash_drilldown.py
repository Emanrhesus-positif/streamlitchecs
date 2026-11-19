"""Drill-down ouvertures → parties → coups, directement dans Streamlit.

Le même parcours existe aussi en Dash dans ``app_dash.py`` (port 8050).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from data import familles, load_coups, load_data
from ui import PLOTLY_CONFIG, apply_theme, style_fig

if os.environ.get("AWP_UNIFIED") != "1":
    st.set_page_config(page_title="AWP — Drill-down", layout="wide", initial_sidebar_state="expanded")

apply_theme()


def _lien_dash() -> str | None:
    """URL publique du Dash (secret Streamlit Cloud ou variable d'environnement)."""
    url = os.environ.get("AWP_DASH_URL")
    if not url:
        try:
            url = st.secrets["AWP_DASH_URL"]
        except Exception:
            return None
    return (url or "").rstrip("/") or None


@st.cache_data
def donnees():
    return load_data(), load_coups()


df, coups = donnees()

st.title("Quelles ouvertures me coûtent des points ?")
st.caption("Cliquez une barre pour lister les parties, puis une ligne pour voir les coups jugés mauvais.")

DASH_URL = _lien_dash()
if DASH_URL:
    c1, c2 = st.columns([1, 3])
    c1.link_button("Ouvrir la version Dash", DASH_URL, width="stretch")
    c2.caption("Le même drill-down, servi par `app_dash.py` (Render).")
    with st.expander("Afficher la version Dash ici", expanded=False):
        components.iframe(DASH_URL, height=900, scrolling=True)
else:
    st.caption(
        "Version Dash en local : `python fil_rouge/app_dash.py` → http://127.0.0.1:8050 "
        "(ou définir `AWP_DASH_URL` pour l'afficher ici)."
    )

n_min = st.slider(
    "Parties minimum par famille d'ouvertures",
    min_value=5,
    max_value=100,
    value=30,
    step=5,
    key="exo4_n_min",
)

fam = familles(df, min_n=n_min)
if fam.empty:
    st.warning("Aucune famille d'ouvertures avec ce minimum de parties.")
    st.stop()

fam_disp = fam.iloc[::-1].reset_index(drop=True)
fig = px.bar(
    fam_disp,
    x="score",
    y="famille",
    orientation="h",
    color="score",
    color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
    range_color=(0, 1),
    text=fam_disp["score"].map(lambda v: f"{v:.2f}"),
    hover_data={"n": True, "gaffes": ":.2f", "score": ":.3f"},
    title=f"Score moyen par famille d'ouvertures (≥ {n_min} parties)",
    labels={
        "score": "Score moyen",
        "famille": "Famille",
        "n": "Parties",
        "gaffes": "Gaffes / partie",
    },
)
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(coloraxis_showscale=False)
fig = style_fig(fig, height=440)
fig.update_layout(margin=dict(l=170, r=35, t=60, b=20))

selection = st.plotly_chart(
    fig,
    width="stretch",
    config=PLOTLY_CONFIG,
    on_select="rerun",
    key="exo4_familles",
)

points = (selection.selection or {}).get("points", []) if selection else []
famille_sel = points[0].get("y") if points else fam.iloc[0]["famille"]

ligne = fam[fam["famille"] == famille_sel]
if not ligne.empty:
    info = ligne.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Famille", str(famille_sel))
    c2.metric("Score moyen", f"{info['score']:.2f}")
    c3.metric("Parties", int(info["n"]))

sous = df[df["ouverture_famille"] == famille_sel].copy()
sous = sous.sort_values("date_jeu", ascending=False)

colonnes = [
    "partie_id",
    "date_jeu",
    "cadence",
    "couleur",
    "resultat",
    "score",
    "gaffes_joueur",
    "ecart_elo",
    "ouverture_nom",
]
colonnes = [c for c in colonnes if c in sous.columns]
table = sous[colonnes].copy()
table["date_jeu"] = table["date_jeu"].dt.strftime("%Y-%m-%d")
if "couleur" in table:
    table["couleur"] = table["couleur"].map({"white": "Blancs", "black": "Noirs"}).fillna(table["couleur"])

st.subheader(f"Parties — {famille_sel}")
etat = st.dataframe(
    table,
    width="stretch",
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key=f"exo4_parties_{famille_sel}",
    column_config={
        "score": st.column_config.NumberColumn("score", format="%.2f"),
        "gaffes_joueur": st.column_config.NumberColumn("gaffes", format="%d"),
        "ecart_elo": st.column_config.NumberColumn("écart Elo", format="%+d"),
    },
)

lignes = getattr(etat.selection, "rows", []) if etat and etat.selection else []
if lignes:
    partie = table.iloc[int(lignes[0])]["partie_id"]
else:
    partie = table.iloc[0]["partie_id"] if not table.empty else None

if partie is None:
    st.info("Aucune partie dans cette famille.")
    st.stop()

st.subheader(f"Coups jugés mauvais — {partie}")
coups_partie = coups[coups["partie_id"] == partie].copy()
coups_partie = coups_partie.sort_values(["ply", "numero_coup"], na_position="last")

if coups_partie.empty:
    st.info("Aucun coup jugé mauvais dans cette partie.")
else:
    colonnes_coups = [
        "numero_coup",
        "couleur",
        "coup",
        "meilleur_coup",
        "jugement",
        "phase",
        "variation_eval_cp",
        "eval_cp",
        "temps_restant_s",
    ]
    colonnes_coups = [c for c in colonnes_coups if c in coups_partie.columns]
    detail = coups_partie[colonnes_coups].copy()
    if "couleur" in detail:
        detail["couleur"] = detail["couleur"].map({"white": "Blancs", "black": "Noirs"}).fillna(detail["couleur"])
    if "phase" in detail:
        detail["phase"] = detail["phase"].map(
            {"opening": "Ouverture", "middlegame": "Milieu", "endgame": "Finale"}
        ).fillna(detail["phase"])
    st.dataframe(
        detail,
        width="stretch",
        hide_index=True,
        column_config={
            "variation_eval_cp": st.column_config.NumberColumn("perte (cp)", format="%d"),
            "eval_cp": st.column_config.NumberColumn("évaluation", format="%d"),
        },
    )
