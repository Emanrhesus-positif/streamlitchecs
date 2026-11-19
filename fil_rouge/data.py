"""Exo 1 : lire mes parties d'échecs. Environ 25 min.

Question : je joue depuis 2023, je stagne, qu'est-ce que je devrais travailler ?
À produire : un DataFrame propre, prêt pour les figures de l'exo 1 et pour l'appli de l'exo 2.
Les colonnes et leurs pièges sont dans data/echecs/LISEZMOI.md : lisez-le d'abord.
Lancer : uv run python fil_rouge/data.py
"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "echecs"

REQUIRED_PARTIES = [
    "partie_id",
    "date_jeu",
    "resultat",
    "elo_joueur",
    "elo_adverse",
    "cadence",
    "ouverture_famille",
    "gaffes_joueur",
]

NUMERIC_COLUMNS = [
    "elo_joueur",
    "elo_adverse",
    "nb_coups",
    "imprecisions_joueur",
    "erreurs_joueur",
    "gaffes_joueur",
    "imprecisions_adverse",
    "erreurs_adverse",
    "gaffes_adverse",
]


def valider(df: pd.DataFrame) -> pd.DataFrame:
    """Plan B : s'arrêter avec un message clair si le fichier n'a pas la forme attendue.

    Colonnes absentes, colonnes entièrement vides, nombres lus comme du texte,
    identifiant de partie en double, résultat inconnu.
    """
    missing = [c for c in REQUIRED_PARTIES if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes absentes : {missing}")

    empty = [c for c in df.columns if df[c].isna().all()]
    if empty:
        raise ValueError(f"Colonnes entièrement vides : {empty}")

    for c in NUMERIC_COLUMNS:
        if c in df.columns and df[c].dtype == object:
            raise ValueError(f"Colonne {c} lue comme du texte (attendu un nombre)")

    if df["partie_id"].duplicated().any():
        n = int(df["partie_id"].duplicated().sum())
        raise ValueError(f"{n} identifiants de partie en double")

    inconnus = set(df["resultat"].dropna()) - {"win", "draw", "lose"}
    if inconnus:
        raise ValueError(f"Résultats inconnus : {sorted(inconnus)}")

    return df


def load_data() -> pd.DataFrame:
    """Une ligne par partie (data/echecs/parties.csv), validée.

    Ajoutez : le résultat de mon point de vue en français, un score (1, 0,5 ou 0),
    l'année, l'heure, et l'écart d'Elo avec l'adversaire. Une cadence vide veut dire
    « aucune » : ne la laissez pas disparaître des filtres.
    Les exos suivants lisent ces colonnes, gardez ces noms : date_jeu (en datetime),
    resultat (victoire, nulle, défaite), score, annee, heure (UTC), ecart_elo
    (Elo de l'adversaire moins le mien), cadence.
    """
    path = DATA / "parties.csv"
    df = pd.read_csv(path)
    df = valider(df)

    # date_jeu en datetime (UTC, sans fuseau écrit dans le fichier -> naive)
    df["date_jeu"] = pd.to_datetime(df["date_jeu"])

    # Résultat en français
    resultat_map = {"win": "victoire", "draw": "nulle", "lose": "défaite"}
    df["resultat"] = df["resultat"].map(resultat_map)

    # Score : 1 victoire, 0.5 nulle, 0 défaite
    score_map = {"victoire": 1, "nulle": 0.5, "défaite": 0}
    df["score"] = df["resultat"].map(score_map)

    # Année et heure (UTC)
    df["annee"] = df["date_jeu"].dt.year
    df["heure"] = df["date_jeu"].dt.hour

    # Écart d'Elo : Elo de l'adversaire moins le mien
    df["ecart_elo"] = df["elo_adverse"] - df["elo_joueur"]

    # Cadence vide = « aucune » (ne pas faire disparaître des filtres)
    df["cadence"] = df["cadence"].fillna("aucune")

    return df


def load_coups() -> pd.DataFrame:
    """Un de mes coups jugés mauvais par ligne (data/echecs/coups_juges.csv)."""
    path = DATA / "coups_juges.csv"
    coups = pd.read_csv(path)

    REQUIRED = ["partie_id", "ply", "couleur", "phase", "jugement", "variation_eval_cp"]
    missing = [c for c in REQUIRED if c not in coups.columns]
    if missing:
        raise ValueError(f"Colonnes absentes dans coups_juges.csv : {missing}")

    return coups


def familles(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    """Score moyen par famille d'ouvertures, la pire d'abord.

    Colonnes : famille, n (parties), score, gaffes (par partie).
    Sous min_n parties le chiffre ne dit rien : écartez la famille.
    """
    d = df[df["ouverture_famille"].notna() & (df["ouverture_famille"] != "")].copy()

    g = (
        d.groupby("ouverture_famille")
        .agg(n=("partie_id", "count"), score=("score", "mean"), gaffes=("gaffes_joueur", "mean"))
        .reset_index()
        .rename(columns={"ouverture_famille": "famille"})
    )

    g = g[g["n"] >= min_n].copy()
    g = g.sort_values("score", ascending=True).reset_index(drop=True)
    return g


if __name__ == "__main__":
    d = load_data()
    print(d.shape)
