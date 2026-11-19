from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RACINE = Path(__file__).resolve().parents[1]
PAGES = [
    RACINE / "fil_rouge" / "01_figures.py",
    RACINE / "fil_rouge" / "pages" / "02_Exo2_Appli_hebdo.py",
    RACINE / "fil_rouge" / "pages" / "04_Exo4_Dash_drilldown.py",
    RACINE / "fil_rouge" / "pages" / "05_Exo5_API_et_clients.py",
    RACINE / "fil_rouge" / "pages" / "06_Exo6_MCP_et_outils.py",
]


@pytest.fixture(autouse=True)
def pas_de_bootstrap(monkeypatch):
    monkeypatch.setenv("AWP_NO_BOOTSTRAP", "1")
    monkeypatch.setenv("AWP_UNIFIED", "1")


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_se_charge_sans_exception(page):
    at = AppTest.from_file(str(page), default_timeout=90)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
