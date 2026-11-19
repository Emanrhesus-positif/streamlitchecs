"""Exo 4 : la même appli en Dash, avec un drill-down. Environ 25 min.

Question : quelles ouvertures coûtent des points, et dans quelles parties ?
À produire : un curseur (parties minimum) et le graphique des familles ; un clic sur une barre
liste les parties, un clic sur une partie liste les coups jugés mauvais, dans deux AG Grid.
Lancer : uv run python fil_rouge/app_dash.py   (http://127.0.0.1:8050)
"""

import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, callback, dcc, html, no_update

from data import familles, load_coups, load_data

app = Dash(__name__, title="Mes parties d'échecs")
server = app.server  # Dash tourne sur Flask

# Données chargées une fois au démarrage
df = load_data()
coups = load_coups()

PARTIES_COLS = [
    "partie_id",
    "date_jeu",
    "couleur",
    "cadence",
    "resultat",
    "score",
    "gaffes_joueur",
    "ouverture_famille",
    "ouverture_nom",
    "ecart_elo",
]
COUPS_COLS = [
    "partie_id",
    "numero_coup",
    "couleur",
    "coup",
    "meilleur_coup",
    "jugement",
    "phase",
    "variation_eval_cp",
    "eval_avant_cp",
    "eval_apres_cp",
]


def _cols_disponibles(cols, frame):
    return [c for c in cols if c in frame.columns]


app.layout = html.Div(
    [
        html.H2("Quelles ouvertures me coûtent des points ? Cliquez une barre"),
        html.Div(
            [
                html.Label("Parties minimum par famille d'ouvertures"),
                dcc.Slider(30, 60, 10, value=30, id="n-min"),
            ],
            style={"maxWidth": "500px", "marginBottom": "10px"},
        ),
        dcc.Graph(id="familles"),
        html.H3("Parties de la famille sélectionnée"),
        dag.AgGrid(
            id="parties",
            columnDefs=[{"field": c} for c in _cols_disponibles(PARTIES_COLS, df)],
            rowData=[],
            dashGridOptions={
                "theme": "legacy",
                "rowSelection": {"mode": "singleRow", "enableClickSelection": True},
            },
            className="ag-theme-alpine-dark",
            columnSize="sizeToFit",
            style={"height": "320px", "width": "100%", "marginBottom": "20px"},
        ),
        html.H3("Coups jugés mauvais de la partie sélectionnée"),
        dag.AgGrid(
            id="coups",
            columnDefs=[{"field": c} for c in _cols_disponibles(COUPS_COLS, coups)],
            rowData=[],
            dashGridOptions={"theme": "legacy"},
            className="ag-theme-alpine-dark",
            columnSize="sizeToFit",
            style={"height": "320px", "width": "100%"},
        ),
    ],
    style={
        "padding": "16px 24px",
        "fontFamily": "Inter, Segoe UI, sans-serif",
        "background": "radial-gradient(circle at 12% 0%, #141d33 0%, #080b14 42%, #03040a 100%)",
        "color": "#e5e7eb",
        "minHeight": "100vh",
    },
)


@callback(Output("familles", "figure"), Input("n-min", "value"))
def maj_familles(n_min):
    """Figure des familles d'ouvertures (la pire en haut) selon le seuil n_min."""
    f = familles(df, n_min)
    if f.empty:
        fig = px.bar(title="Aucune famille avec assez de parties")
        fig.update_layout(xaxis_title="Score moyen", yaxis_title="Famille d'ouverture")
        return fig

    # La pire en haut : familles() renvoie trié score asc, on inverse pour l'affichage horizontal
    f_disp = f.iloc[::-1].reset_index(drop=True)
    fig = px.bar(
        f_disp,
        x="score",
        y="famille",
        orientation="h",
        title=f"Score moyen par famille d'ouvertures (la pire en haut, ≥ {n_min} parties)",
        labels={
            "score": "Score moyen (1 = victoire, 0 = défaite)",
            "famille": "Famille d'ouverture",
            "n": "Parties",
            "gaffes": "Gaffes / partie",
        },
        hover_data=["n", "gaffes"],
        color="score",
        color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
        range_color=(0, 1),
        template="plotly_dark",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        margin=dict(l=170, r=35, t=60, b=20),
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11,18,32,.55)",
        font=dict(color="#e5e7eb"),
        title_font=dict(color="#f8fafc"),
    )
    return fig


@callback(
    Output("parties", "rowData"),
    Output("coups", "rowData", allow_duplicate=True),
    Input("familles", "clickData"),
    prevent_initial_call=True,
)
def afficher_parties(clickData):
    """Liste les parties de la famille cliquée (et vide la grille des coups)."""
    if not clickData or not clickData.get("points"):
        return [], []
    point = clickData["points"][0]
    famille_sel = point.get("y") or point.get("label")
    if not famille_sel:
        return [], []

    subset = df[df["ouverture_famille"] == famille_sel].copy()
    subset = subset.sort_values("date_jeu", ascending=False)
    cols = _cols_disponibles(PARTIES_COLS, subset)
    rows = subset[cols].copy()
    if "date_jeu" in rows.columns:
        rows["date_jeu"] = rows["date_jeu"].astype(str)
    return rows.to_dict("records"), []


@callback(
    Output("coups", "rowData", allow_duplicate=True),
    Input("parties", "selectedRows"),
    prevent_initial_call=True,
)
def afficher_coups(selectedRows):
    """Liste les coups jugés mauvais de la partie sélectionnée."""
    if not selectedRows:
        return []
    partie_id = selectedRows[0].get("partie_id")
    if not partie_id:
        return []

    subset = coups[coups["partie_id"] == partie_id].copy()
    subset = subset.sort_values(["numero_coup", "ply"], na_position="last")
    cols = _cols_disponibles(COUPS_COLS, subset)
    return subset[cols].to_dict("records")


if __name__ == "__main__":
    # debug=True : bouton « Callbacks » en bas à droite, le graphe des callbacks
    app.run(debug=True, port=8050)
