"""Pilote l'appli Streamlit déployée sans navigateur, via son agent API.

C'est la commande `curl` de l'exo 6, en version lisible : une session, un
changement de page, des valeurs de widgets, puis les indicateurs renvoyés par
l'application.

Lancer :
    python fil_rouge/agent_demo.py https://appchecs-pzfcgcn2bfbfqdaetcd4xq.streamlit.app
    python fil_rouge/agent_demo.py https://... --couleur Noirs --cadence blitz
    python fil_rouge/agent_demo.py https://... --list-pages

Prérequis : `server.enableAgentApi = true` côté application (déjà dans
`.streamlit/config.toml`).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests

PAGE_DEFAUT = "Exo2_Appli_hebdo"


def appeler(base: str, payload: dict[str, Any], timeout: float = 60.0) -> dict[str, Any]:
    """POST /_stcore/agent/interact, en attendant la fin d'un run si nécessaire."""
    url = f"{base.rstrip('/')}/_stcore/agent/interact"
    reponse = requests.post(url, json=payload, timeout=timeout)
    data = reponse.json()

    # 202 : le run dépasse agentWaitTimeout et continue. On le collecte avec le session_id.
    if reponse.status_code == 202 and data.get("session_id"):
        return appeler(base, {"session_id": data["session_id"]}, timeout)

    reponse.raise_for_status()
    return data


def metriques(snapshot: dict[str, Any]) -> list[tuple[str, Any]]:
    """Extrait les st.metric de l'arbre, où qu'ils soient."""
    trouvees: list[tuple[str, Any]] = []

    def parcourir(noeud: dict[str, Any]) -> None:
        if noeud.get("type") == "metric":
            props = noeud.get("props", {})
            trouvees.append((props.get("label"), props.get("value")))
        for enfant in noeud.get("children", []) or []:
            parcourir(enfant)

    parcourir(snapshot.get("tree", {}))
    return trouvees


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pilote l'appli AWP via l'agent API Streamlit.")
    parser.add_argument("base", help="URL de l'appli, ex. https://....streamlit.app")
    parser.add_argument("--page", default=PAGE_DEFAUT, help=f"url_path de la page (défaut : {PAGE_DEFAUT})")
    parser.add_argument("--couleur", choices=["Toutes", "Blancs", "Noirs"], help="Filtre couleur")
    parser.add_argument("--cadence", help="Cadence(s), séparées par des virgules : blitz,bullet")
    parser.add_argument("--n-min", type=int, help="Minimum de parties par famille d'ouvertures")
    parser.add_argument("--list-pages", action="store_true", help="Lister les pages puis quitter")
    parser.add_argument("--json", action="store_true", help="Afficher la réponse brute des indicateurs")
    args = parser.parse_args(argv)

    snapshot = appeler(args.base, {})

    if args.list_pages:
        for page in snapshot.get("pages", []):
            print(f"{page.get('url_path')!r:28} {page.get('title')}")
        return 0

    snapshot = appeler(
        args.base,
        {"session_id": snapshot["session_id"], "page": args.page},
    )

    etat: dict[str, Any] = {}
    if args.couleur:
        etat["couleur"] = args.couleur
    if args.cadence:
        etat["cadence"] = [c.strip() for c in args.cadence.split(",") if c.strip()]
    if args.n_min is not None:
        etat["n_min"] = args.n_min
    if etat:
        snapshot = appeler(
            args.base,
            {"session_id": snapshot["session_id"], "widget_state": etat},
        )

    page = snapshot.get("page", {})
    print(f"page    : {page.get('url_path')!r} — {page.get('title')}")
    print(f"statut  : {snapshot.get('status')}")
    resultat = metriques(snapshot)
    for label, valeur in resultat:
        print(f"{label} : {valeur}")

    if args.json:
        print(json.dumps(resultat, ensure_ascii=False))

    return 0 if snapshot.get("status") == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
