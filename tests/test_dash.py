from app_dash import afficher_coups, afficher_parties, maj_familles, reinitialiser


def test_figure_familles_pire_en_haut():
    fig = maj_familles(30)
    assert fig.data
    familles_affichees = list(fig.data[0].y)
    assert familles_affichees[0] == "Scotch Game"
    assert familles_affichees[-1] == "Hungarian Opening"


def test_figure_seuil_60():
    fig = maj_familles(60)
    assert fig.data
    assert "≥ 60" in fig.layout.title.text


def test_figure_seuil_impossible():
    fig = maj_familles(10_000)
    assert fig.layout.title.text == "Aucune famille avec assez de parties"


def test_clic_barre_liste_les_parties():
    rows, coups, resume, titre = afficher_parties(
        {"points": [{"y": "Hungarian Opening"}]}, 30
    )
    assert rows
    assert all(r["ouverture_famille"] == "Hungarian Opening" for r in rows)
    assert len(rows) == 36
    assert coups == []
    assert len(resume) == 4
    assert "Hungarian Opening" in titre
    assert "(36)" in titre


def test_clic_partie_liste_les_coups():
    rows, _, _, _ = afficher_parties({"points": [{"y": "Hungarian Opening"}]}, 30)
    partie = rows[0]["partie_id"]
    detail = afficher_coups([{"partie_id": partie}])
    assert detail
    assert all(c["partie_id"] == partie for c in detail)
    assert all(c["jugement"] for c in detail)


def test_curseur_reinitialise_les_grilles():
    assert reinitialiser(40) == ([], [], [], "Parties de la famille sélectionnée")


def test_clic_vide_ne_casse_rien():
    assert afficher_parties(None, 30) == ([], [], [], "Parties de la famille sélectionnée")
    assert afficher_coups([]) == []
