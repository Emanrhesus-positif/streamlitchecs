"""L'appli hebdo : filtres, indicateurs et figures sur les parties filtrées.

Lancer seul : streamlit run fil_rouge/pages/02_Exo2_Appli_hebdo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import streamlit as st

from chess_sim import charger_moments, render_simulateur, selecteur_moments
from data import familles, load_coups, load_data
from ui import PLOTLY_CONFIG, apply_theme, style_fig

if os.environ.get("AWP_UNIFIED") != "1":
    st.set_page_config(page_title="AWP — Appli hebdo", layout="wide", initial_sidebar_state="expanded")

apply_theme()
print("relance")  # visible dans le terminal à chaque interaction


@st.cache_data
def donnees():
    return load_data(), load_coups()


@st.cache_data
def moments_critiques():
    return charger_moments()


df, coups = donnees()
moments = moments_critiques()

st.title("Je joue depuis 2023, je stagne : qu'est-ce que je devrais travailler ?")
st.caption("Tous les chiffres et toutes les figures suivent les filtres de la barre latérale.")

# ---------------------------------------------------------------------------
# Filtres
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filtres")

    cadences = sorted(df["cadence"].dropna().astype(str).unique().tolist())
    cadence_sel = st.multiselect(
        "Cadence",
        options=cadences,
        default=cadences,
        key="cadence",
    )

    min_date = df["date_jeu"].min().date()
    max_date = df["date_jeu"].max().date()
    periode = st.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="periode",
    )

    couleur_sel = st.selectbox(
        "Couleur",
        options=["Toutes", "white", "black"],
        format_func=lambda x: {"Toutes": "Toutes", "white": "Blancs", "black": "Noirs"}[x],
        key="couleur",
    )

    n_min = st.slider(
        "Min. parties par famille d'ouvertures",
        min_value=5,
        max_value=100,
        value=30,
        step=5,
        key="n_min",
    )

if not cadence_sel:
    st.warning("Choisissez au moins une cadence dans la barre latérale.")
    st.stop()

if not isinstance(periode, (tuple, list)) or len(periode) != 2:
    st.warning("Sélectionnez une période complète (date de début et date de fin).")
    st.stop()

debut = pd.to_datetime(periode[0])
fin = pd.to_datetime(periode[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

vue = df[df["cadence"].isin(cadence_sel)]
vue = vue[(vue["date_jeu"] >= debut) & (vue["date_jeu"] <= fin)]
if couleur_sel != "Toutes":
    vue = vue[vue["couleur"] == couleur_sel]

if vue.empty:
    st.warning("Aucune partie ne correspond aux filtres sélectionnés.")
    st.stop()

# ---------------------------------------------------------------------------
# Indicateurs
# ---------------------------------------------------------------------------
m1, m2, m3 = st.columns(3)
m1.metric("Parties", f"{len(vue):,}".replace(",", " "))
m2.metric("Score moyen", f"{100 * vue['score'].mean():.1f} %")
m3.metric("Gaffes par partie", f"{vue['gaffes_joueur'].mean():.2f}")

# ---------------------------------------------------------------------------
# Deux figures côte à côte
# ---------------------------------------------------------------------------
phase_order = ["opening", "middlegame", "endgame"]
phase_labels = {"opening": "Ouverture", "middlegame": "Milieu", "endgame": "Finale"}
coups_vue = coups[coups["partie_id"].isin(vue["partie_id"])].copy()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Familles d'ouvertures")
    fam = familles(vue, min_n=n_min)
    if fam.empty:
        st.info(f"Pas assez de parties par famille pour afficher ce graphique (minimum {n_min}).")
    else:
        fam_disp = fam.iloc[::-1].reset_index(drop=True)
        fig_fam = px.bar(
            fam_disp,
            x="score",
            y="famille",
            orientation="h",
            color="score",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            range_color=(0, 1),
            text=fam_disp["score"].map(lambda v: f"{v:.2f}"),
            hover_data={"n": True, "gaffes": ":.2f", "score": ":.3f"},
            title="Score moyen par famille — la pire en haut",
            labels={
                "score": "Score moyen",
                "famille": "Famille",
                "n": "Parties",
                "gaffes": "Gaffes / partie",
            },
        )
        fig_fam.update_traces(textposition="outside", cliponaxis=False)
        fig_fam.update_layout(coloraxis_showscale=False)
        fig_fam = style_fig(fig_fam, height=430)
        fig_fam.update_layout(margin=dict(l=160, r=30, t=60, b=20))

        selection = st.plotly_chart(
            fig_fam,
            width="stretch",
            config=PLOTLY_CONFIG,
            on_select="rerun",
            key="fig_familles",
        )
        points = (selection.selection or {}).get("points", []) if selection else []
        cliquees = [p.get("y") for p in points if p.get("y")]
        if cliquees:
            st.caption("Familles sélectionnées")
            detail = fam[fam["famille"].isin(cliquees)].copy()
            detail["score"] = detail["score"].round(3)
            detail["gaffes"] = detail["gaffes"].round(3)
            st.dataframe(detail, width="stretch", hide_index=True)

with col2:
    st.subheader("Phases des gaffes")
    gaffes = (
        coups_vue[coups_vue["jugement"] == "blunder"]
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

    fig_gaffes = px.bar(
        gaffes,
        x="phase_label",
        y="nb_gaffes",
        color="phase_label",
        color_discrete_map={"Ouverture": "#60a5fa", "Milieu": "#f59e0b", "Finale": "#a78bfa"},
        text="nb_gaffes",
        title="Gaffes par phase de la partie",
        labels={"phase_label": "Phase", "nb_gaffes": "Gaffes"},
    )
    fig_gaffes.update_traces(textposition="outside", cliponaxis=False)
    fig_gaffes.update_layout(showlegend=False)
    fig_gaffes = style_fig(fig_gaffes, height=430)

    selection2 = st.plotly_chart(
        fig_gaffes,
        width="stretch",
        config=PLOTLY_CONFIG,
        on_select="rerun",
        key="fig_gaffes",
    )
    points2 = (selection2.selection or {}).get("points", []) if selection2 else []
    phases_cliquees = [p.get("x") for p in points2 if p.get("x")]
    if phases_cliquees:
        inv = {v: k for k, v in phase_labels.items()}
        phases = [inv.get(x, x) for x in phases_cliquees]
        st.caption("Gaffes des phases sélectionnées")
        detail = coups_vue[
            (coups_vue["jugement"] == "blunder") & (coups_vue["phase"].isin(phases))
        ][["partie_id", "numero_coup", "coup", "meilleur_coup", "phase", "variation_eval_cp"]]
        st.dataframe(
            detail.sort_values(["partie_id", "numero_coup"]).head(100),
            width="stretch",
            hide_index=True,
        )

# ---------------------------------------------------------------------------
# Figure supplémentaire : l'heure
# ---------------------------------------------------------------------------
with st.expander("Score selon l'heure UTC", expanded=False):
    par_heure = vue.groupby("heure", as_index=False).agg(
        parties=("score", "size"), score=("score", "mean")
    )
    par_heure = par_heure[par_heure["parties"] >= 30].sort_values("heure")
    if par_heure.empty:
        st.info("Pas assez de parties par heure (≥ 30) dans la sélection.")
    else:
        fig_heure = px.line(
            par_heure,
            x="heure",
            y="score",
            markers=True,
            title="Score moyen selon l'heure UTC (≥ 30 parties par heure)",
            labels={"heure": "Heure UTC", "score": "Score moyen"},
        )
        fig_heure.update_traces(
            line=dict(color="#60a5fa", width=2.5),
            marker=dict(size=7, color="#93c5fd"),
        )
        fig_heure.add_hline(
            y=float(vue["score"].mean()),
            line_dash="dot",
            line_color="rgba(148,163,184,.8)",
            annotation_text=f"moyenne {vue['score'].mean():.2f}",
            annotation_position="top left",
            annotation_font_color="#cbd5e1",
        )
        fig_heure = style_fig(fig_heure, height=380)
        fig_heure.update_yaxes(range=[0, 1])
        st.plotly_chart(fig_heure, width="stretch", config=PLOTLY_CONFIG)

# ---------------------------------------------------------------------------
# Simulateur filtré
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Rejouer les moments critiques des parties filtrées")
st.caption("Sélectionnez une partie, puis utilisez Jouer / Précédent / Suivant / Tout lire.")

partie, _ = selecteur_moments(vue, moments, key_prefix="exo2_sim")
if partie:
    render_simulateur(partie, moments, label=f"Partie {partie}")
else:
    st.info("Aucune partie avec un moment critique exploitable dans cette sélection.")
