"""Exo 4 : la même appli en Dash, avec un drill-down. Environ 25 min.

Question : quelles ouvertures coûtent des points, et dans quelles parties ?
À produire : un curseur (parties minimum) et le graphique des familles ; un clic sur une barre
liste les parties, un clic sur une partie liste les coups jugés mauvais, dans deux AG Grid.
Lancer : python fil_rouge/app_dash.py   (http://127.0.0.1:8050)
"""

import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, State, callback, dcc, html

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

LABELS = {
    "partie_id": "Partie",
    "date_jeu": "Date",
    "couleur": "Couleur",
    "cadence": "Cadence",
    "resultat": "Résultat",
    "score": "Score",
    "gaffes_joueur": "Gaffes",
    "ouverture_famille": "Famille",
    "ouverture_nom": "Ouverture",
    "ecart_elo": "Écart Elo",
    "numero_coup": "Coup n°",
    "coup": "Coup joué",
    "meilleur_coup": "Meilleur coup",
    "jugement": "Jugement",
    "phase": "Phase",
    "variation_eval_cp": "Perte (cp)",
    "eval_avant_cp": "Éval. avant",
    "eval_apres_cp": "Éval. après",
}

COLONNES_NUMERIQUES = {
    "score": "params.value == null ? '' : Number(params.value).toFixed(2)",
    "gaffes_joueur": "params.value == null ? '' : Number(params.value).toFixed(0)",
    "ecart_elo": "params.value == null ? '' : (params.value > 0 ? '+' : '') + Number(params.value).toFixed(0)",
    "variation_eval_cp": "params.value == null ? '' : Number(params.value).toFixed(0)",
    "eval_avant_cp": "params.value == null ? '' : Number(params.value).toFixed(0)",
    "eval_apres_cp": "params.value == null ? '' : Number(params.value).toFixed(0)",
}


def _cols_disponibles(cols, frame):
    return [c for c in cols if c in frame.columns]


def _column_defs(cols):
    defs = []
    for c in cols:
        d = {"field": c, "headerName": LABELS.get(c, c)}
        if c in COLONNES_NUMERIQUES:
            d["type"] = "numericColumn"
            d["valueFormatter"] = {"function": COLONNES_NUMERIQUES[c]}
        if c == "phase":
            d["valueFormatter"] = {
                "function": "({opening:'Ouverture', middlegame:'Milieu', endgame:'Finale'})[params.value] || params.value"
            }
        if c == "couleur":
            d["valueFormatter"] = {
                "function": "({white:'Blancs', black:'Noirs'})[params.value] || params.value"
            }
        if c == "jugement":
            d["valueFormatter"] = {
                "function": "({inaccuracy:'Imprécision', mistake:'Erreur', blunder:'Gaffe'})[params.value] || params.value"
            }
        defs.append(d)
    return defs


app.layout = html.Div(
    [
        html.H1("Quelles ouvertures me coûtent des points ?"),
        html.P(
            "Cliquez une barre pour lister les parties, puis une ligne pour voir les coups jugés mauvais.",
            style={"color": "#9aa4b2", "marginTop": "-6px"},
        ),
        html.Div(
            [
                html.Label("Parties minimum par famille d'ouvertures"),
                dcc.Slider(30, 60, 10, value=30, id="n-min"),
            ],
            style={"maxWidth": "500px", "marginBottom": "10px"},
        ),
        dcc.Graph(id="familles"),
        html.Div(id="resume", style={"display": "flex", "gap": "10px", "margin": "6px 0 14px"}),
        html.H3(id="titre-parties", children="Parties de la famille sélectionnée"),
        dag.AgGrid(
            id="parties",
            columnDefs=_column_defs(_cols_disponibles(PARTIES_COLS, df)),
            rowData=[],
            dashGridOptions={
                "theme": "legacy",
                "rowSelection": {"mode": "singleRow", "enableClickSelection": True},
            },
            defaultColDef={"sortable": True, "resizable": True},
            dangerously_allow_code=True,
            className="ag-theme-alpine-dark",
            columnSize="sizeToFit",
            style={"height": "320px", "width": "100%", "marginBottom": "20px"},
        ),
        html.H3("Coups jugés mauvais de la partie sélectionnée"),
        dag.AgGrid(
            id="coups",
            columnDefs=_column_defs(_cols_disponibles(COUPS_COLS, coups)),
            rowData=[],
            dashGridOptions={"theme": "legacy"},
            defaultColDef={"sortable": True, "resizable": True},
            dangerously_allow_code=True,
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

    # familles() trie du pire au meilleur : on inverse pour que le pire soit en haut
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


def _kpi(label, valeur):
    return html.Div(
        [
            html.Div(label, style={"fontSize": "11px", "color": "#9aa4b2", "textTransform": "uppercase"}),
            html.Div(valeur, style={"fontSize": "18px", "fontWeight": "600", "color": "#f8fafc"}),
        ],
        style={
            "background": "rgba(255,255,255,.055)",
            "border": "1px solid rgba(255,255,255,.13)",
            "borderRadius": "12px",
            "padding": "8px 14px",
        },
    )


@callback(
    Output("parties", "rowData"),
    Output("coups", "rowData", allow_duplicate=True),
    Output("resume", "children"),
    Output("titre-parties", "children"),
    Input("familles", "clickData"),
    State("n-min", "value"),
    prevent_initial_call=True,
)
def afficher_parties(clickData, n_min):
    """Liste les parties de la famille cliquée (et vide la grille des coups)."""
    if not clickData or not clickData.get("points"):
        return [], [], [], "Parties de la famille sélectionnée"
    point = clickData["points"][0]
    famille_sel = point.get("y") or point.get("label")
    if not famille_sel:
        return [], [], [], "Parties de la famille sélectionnée"

    info = familles(df, n_min)
    ligne = info[info["famille"] == famille_sel]
    resume = []
    if not ligne.empty:
        r = ligne.iloc[0]
        resume = [
            _kpi("Famille", str(famille_sel)),
            _kpi("Score moyen", f"{r['score']:.2f}"),
            _kpi("Parties", f"{int(r['n'])}"),
            _kpi("Gaffes / partie", f"{r['gaffes']:.2f}"),
        ]

    subset = df[df["ouverture_famille"] == famille_sel].copy()
    subset = subset.sort_values("date_jeu", ascending=False)
    cols = _cols_disponibles(PARTIES_COLS, subset)
    rows = subset[cols].copy()
    if "date_jeu" in rows.columns:
        rows["date_jeu"] = rows["date_jeu"].dt.strftime("%Y-%m-%d")
    return (
        rows.to_dict("records"),
        [],
        resume,
        f"Parties — {famille_sel} ({len(rows)})",
    )


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


@callback(
    Output("parties", "rowData", allow_duplicate=True),
    Output("coups", "rowData", allow_duplicate=True),
    Output("resume", "children", allow_duplicate=True),
    Output("titre-parties", "children", allow_duplicate=True),
    Input("n-min", "value"),
    prevent_initial_call=True,
)
def reinitialiser(n_min):
    """Le changement de seuil invalide la famille et la partie sélectionnées."""
    return [], [], [], "Parties de la famille sélectionnée"


if __name__ == "__main__":
    # debug=True : bouton « Callbacks » en bas à droite, le graphe des callbacks
    app.run(debug=True, port=8050, host="127.0.0.1")
