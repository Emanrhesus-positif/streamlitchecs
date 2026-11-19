"""Logique de service partagée par l'API FastAPI et par les pages Streamlit.

Les fonctions renvoient exactement les mêmes structures que les endpoints de
``api.py``. Elles servent de repli quand l'API n'est pas joignable, notamment
sur Streamlit Community Cloud où seul le processus Streamlit tourne.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from data import familles, load_data

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"

df = load_data()

try:
    model = joblib.load(MODEL_PATH)
except Exception:  # modèle absent ou version incompatible : /predict répondra None
    model = None

PARTIES_COLS = [
    "partie_id",
    "date_jeu",
    "cadence",
    "couleur",
    "resultat",
    "score",
    "gaffes_joueur",
    "ouverture_famille",
    "ouverture_nom",
    "ecart_elo",
    "elo_joueur",
    "elo_adverse",
    "nb_coups",
]


def df_to_records(frame: pd.DataFrame) -> list[dict]:
    """Convertit un DataFrame en enregistrements JSON-sérialisables."""
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    out = out.where(pd.notna(out), None)
    return out.to_dict(orient="records")


def ouvertures_records(cadence: str | None = None, min_n: int = 30) -> list[dict]:
    """Familles d'ouvertures, la pire d'abord (même sortie que GET /ouvertures)."""
    vue = df
    if cadence is not None:
        vue = vue[vue["cadence"] == cadence]
    return df_to_records(familles(vue, min_n=min_n))


def parties_records(
    cadence: str | None = None,
    couleur: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Parties filtrées, les plus récentes d'abord (même sortie que GET /parties)."""
    vue = df.copy()
    if cadence is not None:
        vue = vue[vue["cadence"] == cadence]
    if couleur is not None:
        vue = vue[vue["couleur"] == couleur]

    vue = vue.sort_values("date_jeu", ascending=False).head(limit)
    cols = [c for c in PARTIES_COLS if c in vue.columns]
    return df_to_records(vue[cols])


def predire_proba(
    couleur: str,
    cadence: str,
    ecart_elo: float,
    heure: int,
) -> float | None:
    """Probabilité de victoire estimée (même calcul que POST /predict)."""
    if model is None:
        return None

    X = pd.DataFrame(
        [
            {
                "couleur": couleur,
                "cadence": cadence,
                "ecart_elo": float(ecart_elo),
                "heure": int(heure),
            }
        ]
    )
    proba = model.predict_proba(X)[0]
    classes = list(getattr(model, "classes_", [False, True]))
    if True in classes:
        return float(proba[classes.index(True)])
    return float(proba[-1])
