"""Exo 5 : le service FastAPI. Environ 45 min.

Question : mes parties derrière une API que n'importe quel client peut appeler (votre appli, puis l'agent de l'exo 6).
À produire : GET /ouvertures et GET /parties, paramètres validés (une cadence inconnue renvoie 422, pas une liste vide).
Ensuite : app_api.py, ou votre appli de l'exo 2 ou de l'exo 4, appelle cette API au lieu de lire les CSV.
Bonus : POST /predict avec le modèle fourni (fil_rouge/model.joblib, déjà entraîné), puis client.py.
Lancer : uv run uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000 --reload
Documentation interactive : http://127.0.0.1:8000/docs
"""

from typing import Literal, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from serving import ouvertures_records, parties_records, predire_proba

app = FastAPI(title="Mes parties d'échecs", version="1.0")

CadenceOuvertures = Literal["bullet", "blitz", "rapid"]
Couleur = Literal["white", "black"]
CadencePartie = Literal["aucune", "bullet", "blitz", "rapid", "classical"]


@app.get("/ouvertures")
def get_ouvertures(
    cadence: Optional[CadenceOuvertures] = None,
    min_n: int = Query(30, ge=1),
):
    """Familles d'ouvertures, la pire d'abord. cadence invalide -> 422 (validation Literal)."""
    return ouvertures_records(cadence, min_n=min_n)


@app.get("/parties")
def get_parties(
    cadence: Optional[CadencePartie] = None,
    couleur: Optional[Couleur] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Parties filtrées (plus récentes d'abord), avec paramètres validés."""
    return parties_records(cadence, couleur, limit)


class Partie(BaseModel):
    couleur: Couleur
    cadence: Literal["aucune", "bullet", "blitz", "rapid", "classical"]
    ecart_elo: float = Field(..., description="Elo adverse moins Elo joueur")
    heure: int = Field(..., ge=0, le=23, description="Heure UTC (0-23)")


@app.post("/predict")
def predict(partie: Partie):
    """Probabilité de victoire estimée par le modèle fourni (bonus)."""
    proba = predire_proba(partie.couleur, partie.cadence, partie.ecart_elo, partie.heure)
    if proba is None:
        return {"proba_victoire": None, "detail": "Modèle indisponible"}
    return {"proba_victoire": proba}
