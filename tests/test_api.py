import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_ouvertures_triees_et_filtrees():
    r = client.get("/ouvertures", params={"min_n": 30})
    assert r.status_code == 200
    data = r.json()
    assert data
    assert all({"famille", "n", "score", "gaffes"} <= set(row) for row in data)
    assert [row["score"] for row in data] == sorted(row["score"] for row in data)


def test_ouvertures_cadence_littérale():
    assert client.get("/ouvertures", params={"cadence": "blitz"}).status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {"cadence": "foo"},
        {"min_n": 0},
    ],
)
def test_ouvertures_parametres_invalides(params):
    assert client.get("/ouvertures", params=params).status_code == 422


def test_parties_limite():
    r = client.get("/parties", params={"limit": 5})
    assert r.status_code == 200
    assert len(r.json()) == 5


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 501},
        {"couleur": "bleu"},
        {"cadence": "foo"},
    ],
)
def test_parties_parametres_invalides(params):
    assert client.get("/parties", params=params).status_code == 422


def test_predict():
    r = client.post(
        "/predict",
        json={"couleur": "white", "cadence": "blitz", "ecart_elo": 0, "heure": 20},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["proba_victoire"] is not None
    assert 0 <= body["proba_victoire"] <= 1


@pytest.mark.parametrize(
    "body",
    [
        {"couleur": "white", "cadence": "blitz", "ecart_elo": 0, "heure": 24},
        {"couleur": "bleu", "cadence": "blitz", "ecart_elo": 0, "heure": 20},
        {"couleur": "white", "cadence": "foo", "ecart_elo": 0, "heure": 20},
    ],
)
def test_predict_parametres_invalides(body):
    assert client.post("/predict", json=body).status_code == 422
