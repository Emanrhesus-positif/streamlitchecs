import pandas as pd

from serving import (
    df_to_records,
    ouvertures_records,
    parties_records,
    predire_proba,
)


def test_ouvertures_meme_sortie_que_api():
    data = ouvertures_records(None, min_n=30)
    assert len(data) == 19
    assert all({"famille", "n", "score", "gaffes"} <= set(row) for row in data)
    assert [row["score"] for row in data] == sorted(row["score"] for row in data)
    assert data[0]["famille"] == "Hungarian Opening"


def test_ouvertures_filtre_cadence():
    data = ouvertures_records("blitz", min_n=30)
    assert data
    assert all(row["n"] >= 30 for row in data)


def test_parties_filtre_et_limite():
    data = parties_records("rapid", "black", limit=5)
    assert len(data) == 5
    assert all(row["cadence"] == "rapid" and row["couleur"] == "black" for row in data)
    dates = [row["date_jeu"] for row in data]
    assert dates == sorted(dates, reverse=True)


def test_dates_serialisees_en_texte():
    frame = pd.DataFrame({"date_jeu": pd.to_datetime(["2026-01-02", None])})
    records = df_to_records(frame)
    assert records[0]["date_jeu"] == "2026-01-02T00:00:00"
    assert records[1]["date_jeu"] is None


def test_predict_proba_bornee():
    proba = predire_proba("white", "blitz", 0, 20)
    assert proba is not None
    assert 0 <= proba <= 1


def test_predict_ecart_elo_fait_varier_la_proba():
    faible_adverse = predire_proba("white", "blitz", -300, 20)
    fort_adverse = predire_proba("white", "blitz", 300, 20)
    assert faible_adverse > fort_adverse


def test_predict_couleur_change_la_proba():
    blancs = predire_proba("white", "blitz", 0, 20)
    noirs = predire_proba("black", "blitz", 0, 20)
    assert 0 <= blancs <= 1 and 0 <= noirs <= 1
    assert abs(blancs - noirs) > 1e-6
