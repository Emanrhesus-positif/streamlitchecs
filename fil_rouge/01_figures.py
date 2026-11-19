"""Trois figures Plotly et un simulateur pour répondre à « où je perds des points ».

Lancer seul : streamlit run fil_rouge/01_figures.py
Dans le serveur unifié : streamlit run fil_rouge/app.py (cette page est l'accueil).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from single_instance import bootstrap_streamlit_app

bootstrap_streamlit_app(__file__, port=8501)

import pandas as pd
import plotly.express as px
import streamlit as st

from chess_sim import charger_moments, render_simulateur, selecteur_moments
from data import familles, load_coups, load_data
from ui import PLOTLY_CONFIG, apply_theme, style_fig

if os.environ.get("AWP_UNIFIED") != "1":
    st.set_page_config(
        page_title="AWP — Échecs",
        layout="wide",
        initial_sidebar_state="expanded",
    )

apply_theme()

# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------
df = load_data()


@st.cache_data
def get_moments() -> pd.DataFrame:
    return charger_moments()


moments = get_moments()

st.title("Où ce joueur perd-il des points ?")
st.caption(f"{len(df):,} parties · {df['date_jeu'].min():%Y-%m-%d} → {df['date_jeu'].max():%Y-%m-%d}".replace(",", " "))

# ---------------------------------------------------------------------------
# 1. Score par famille d'ouvertures
# ---------------------------------------------------------------------------
fam = familles(df, min_n=30)
fam_disp = fam.iloc[::-1].reset_index(drop=True)

fig1 = px.bar(
    fam_disp,
    x="score",
    y="famille",
    orientation="h",
    color="score",
    color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
    range_color=(0, 1),
    text=fam_disp["score"].map(lambda v: f"{v:.2f}"),
    hover_data={"n": True, "gaffes": ":.2f", "score": ":.3f"},
    title="Score moyen par famille d'ouvertures — la pire en haut (≥ 30 parties)",
    labels={
        "score": "Score moyen (1 = victoire, 0 = défaite)",
        "famille": "Famille d'ouverture",
        "n": "Parties",
        "gaffes": "Gaffes / partie",
    },
)
fig1.update_traces(textposition="outside", cliponaxis=False)
fig1.update_layout(coloraxis_showscale=False)
fig1 = style_fig(fig1, height=460)
fig1.update_layout(margin=dict(l=180, r=40, t=64, b=30))

# ---------------------------------------------------------------------------
# 2. Gaffes par phase
# ---------------------------------------------------------------------------
coups = load_coups()
phase_order = ["opening", "middlegame", "endgame"]
phase_labels = {"opening": "Ouverture", "middlegame": "Milieu", "endgame": "Finale"}

gaffes = (
    coups[coups["jugement"] == "blunder"]
    .groupby("phase", dropna=False)
    .size()
    .reset_index(name="nb_gaffes")
)
gaffes = (
    pd.DataFrame({"phase": phase_order})
    .merge(gaffes, on="phase", how="left")
    .fillna({"nb_gaffes": 0})
)
gaffes["nb_gaffes"] = gaffes["nb_gaffes"].astype(int)
gaffes["phase_label"] = gaffes["phase"].map(phase_labels)
gaffes["part"] = gaffes["nb_gaffes"] / max(1, gaffes["nb_gaffes"].sum())

fig2 = px.bar(
    gaffes,
    x="phase_label",
    y="nb_gaffes",
    color="phase_label",
    color_discrete_map={"Ouverture": "#60a5fa", "Milieu": "#f59e0b", "Finale": "#a78bfa"},
    text="nb_gaffes",
    custom_data=["part"],
    title="Nombre de gaffes par phase de la partie",
    labels={"phase_label": "Phase", "nb_gaffes": "Nombre de gaffes"},
)
fig2.update_traces(
    textposition="outside",
    cliponaxis=False,
    hovertemplate="%{x}<br>%{y} gaffes<br>%{customdata[0]:.1%} des gaffes<extra></extra>",
)
fig2.update_layout(showlegend=False)
fig2 = style_fig(fig2, height=430)

# ---------------------------------------------------------------------------
# 3. Score selon l'heure UTC
# ---------------------------------------------------------------------------
par_heure = df.groupby("heure", as_index=False).agg(
    parties=("score", "size"), score=("score", "mean")
)
par_heure = par_heure[par_heure["parties"] >= 30].sort_values("heure")
moyenne = float(df["score"].mean())

fig3 = px.line(
    par_heure,
    x="heure",
    y="score",
    markers=True,
    title="Score moyen selon l'heure de la partie (UTC, ≥ 30 parties par heure)",
    labels={"heure": "Heure UTC", "score": "Score moyen"},
)
fig3.update_traces(
    line=dict(color="#60a5fa", width=2.5),
    marker=dict(size=7, color="#93c5fd", line=dict(width=1, color="#0b1220")),
)
fig3.add_hline(
    y=moyenne,
    line_dash="dot",
    line_color="rgba(148, 163, 184, 0.8)",
    annotation_text=f"moyenne {moyenne:.2f}",
    annotation_position="top left",
    annotation_font_color="#cbd5e1",
)
fig3 = style_fig(fig3, height=430)
fig3.update_yaxes(range=[0, 1])

# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------
st.subheader("1 · Les ouvertures qui coûtent le plus")
st.plotly_chart(fig1, width="stretch", config=PLOTLY_CONFIG)

st.subheader("2 · Les phases où tombent les gaffes")
st.plotly_chart(fig2, width="stretch", config=PLOTLY_CONFIG)

st.subheader("3 · Les heures où le score baisse")
st.plotly_chart(fig3, width="stretch", config=PLOTLY_CONFIG)

# ---------------------------------------------------------------------------
# Réponse
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Réponse")

pire_famille = fam.iloc[0] if not fam.empty else None
top_phase = gaffes.sort_values("nb_gaffes", ascending=False).iloc[0] if not gaffes.empty else None
pire_heure = par_heure.sort_values("score").iloc[0] if not par_heure.empty else None

c1, c2, c3 = st.columns(3)
if pire_famille is not None:
    c1.metric(
        "Ouverture la plus faible",
        str(pire_famille["famille"]),
        f"{pire_famille['score']:.2f} · {int(pire_famille['n'])} parties",
    )
if top_phase is not None:
    c2.metric(
        "Phase la plus coûteuse",
        str(top_phase["phase_label"]),
        f"{int(top_phase['nb_gaffes'])} gaffes",
    )
if pire_heure is not None:
    c3.metric(
        "Heure la plus faible",
        f"{int(pire_heure['heure'])} h UTC",
        f"score {pire_heure['score']:.2f}",
    )

phrase = []
if top_phase is not None:
    phrase.append(
        f"en **{top_phase['phase_label'].lower()}** de partie "
        f"({int(top_phase['nb_gaffes'])} gaffes)"
    )
if pire_famille is not None:
    phrase.append(
        f"avec **{pire_famille['famille']}** "
        f"(score {pire_famille['score']:.2f} sur {int(pire_famille['n'])} parties)"
    )
if pire_heure is not None:
    phrase.append(
        f"aux parties jouées vers **{int(pire_heure['heure'])} h UTC** "
        f"(score {pire_heure['score']:.2f})"
    )
if phrase:
    st.markdown("Le joueur perd surtout des points " + ", ".join(phrase) + ".")

# ---------------------------------------------------------------------------
# Simulateur pas à pas
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Rejouer les moments critiques")
st.caption(
    "Choisissez une partie, puis **Jouer le coup**, **Précédent / Suivant** ou **Tout lire**. "
    "Chaque étape rejoue le coup fautif depuis sa position et affiche le meilleur coup."
)

partie, _ = selecteur_moments(df, moments, key_prefix="sim1")
if partie:
    render_simulateur(partie, moments, label=f"Partie {partie}")
else:
    st.info("Aucune partie avec un moment critique exploitable.")
