from agent_demo import metriques


def test_metriques_trouvees_dans_les_containers_imbriques():
    snapshot = {
        "tree": {
            "type": "root",
            "children": [
                {
                    "type": "main",
                    "children": [
                        {
                            "type": "columns",
                            "children": [
                                {"type": "metric", "props": {"label": "Parties", "value": "3 023"}},
                                {"type": "metric", "props": {"label": "Score moyen", "value": "52.3 %"}},
                            ],
                        }
                    ],
                }
            ],
        }
    }
    assert metriques(snapshot) == [("Parties", "3 023"), ("Score moyen", "52.3 %")]


def test_metriques_arbre_vide():
    assert metriques({}) == []
