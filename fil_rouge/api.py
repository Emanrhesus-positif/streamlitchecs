"""Exo 5 : le service FastAPI. Environ 45 min.

Question : mes parties derrière une API que n'importe quel client peut appeler (votre appli, puis l'agent de l'exo 6).
À produire : GET /ouvertures et GET /parties, paramètres validés (une cadence inconnue renvoie 422, pas une liste vide).
Ensuite : app_api.py, ou votre appli de l'exo 2 ou de l'exo 4, appelle cette API au lieu de lire les CSV.
Bonus : POST /predict avec le modèle fourni (fil_rouge/model.joblib, déjà entraîné), puis client.py.
Lancer : uv run uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000 --reload
Documentation interactive : http://127.0.0.1:8000/docs
"""

from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from data import familles, load_data

app = FastAPI(title="Mes parties d'échecs", version="1.0")

# Charger les données une fois, au démarrage
df = load_data()

# Modèle fourni (bonus /predict)
MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
try:
    model = joblib.load(MODEL_PATH)
except Exception:
    model = None


CadenceOuvertures = Literal["bullet", "blitz", "rapid"]
Couleur = Literal["white", "black"]
CadencePartie = Literal["aucune", "bullet", "blitz", "rapid", "classical"]


def _df_to_records(frame: pd.DataFrame):
    """Convertit un DataFrame en enregistrements JSON-sérialisables."""
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    # NaN/NaT -> None
    out = out.where(pd.notna(out), None)
    return out.to_dict(orient="records")


@app.get("/ouvertures")
def get_ouvertures(
    cadence: Optional[CadenceOuvertures] = None,
    min_n: int = Query(30, ge=1),
):
    """Familles d'ouvertures, la pire d'abord. cadence invalide -> 422 (validation Literal)."""
    vue = df
    if cadence is not None:
        vue = vue[vue["cadence"] == cadence]
    res = familles(vue, min_n=min_n)
    return _df_to_records(res)


@app.get("/parties")
def get_parties(
    cadence: Optional[CadencePartie] = None,
    couleur: Optional[Couleur] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Parties filtrées (plus récentes d'abord), avec paramètres validés."""
    vue = df.copy()
    if cadence is not None:
        vue = vue[vue["cadence"] == cadence]
    if couleur is not None:
        vue = vue[vue["couleur"] == couleur]

    vue = vue.sort_values("date_jeu", ascending=False).head(limit)

    cols = [
        c
        for c in [
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
        if c in vue.columns
    ]
    return _df_to_records(vue[cols])


class Partie(BaseModel):
    couleur: Couleur
    cadence: Literal["aucune", "bullet", "blitz", "rapid", "classical"]
    ecart_elo: float = Field(..., description="Elo adverse moins Elo joueur")
    heure: int = Field(..., ge=0, le=23, description="Heure UTC (0-23)")


@app.post("/predict")
def predict(partie: Partie):
    """Probabilité de victoire estimée par le modèle fourni (bonus)."""
    if model is None:
        return {"proba_victoire": None, "detail": "Modèle indisponible"}

    X = pd.DataFrame(
        [
            {
                "couleur": partie.couleur,
                "cadence": partie.cadence,
                "ecart_elo": partie.ecart_elo,
                "heure": partie.heure,
            }
        ]
    )
    proba = model.predict_proba(X)[0]
    # classes typiques [False, True] -> proba de victoire = proba de True
    classes = list(getattr(model, "classes_", [False, True]))
    if True in classes:
        p = float(proba[classes.index(True)])
    else:
        p = float(proba[-1])
    return {"proba_victoire": p}
