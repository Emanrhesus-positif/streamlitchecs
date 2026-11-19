"""Exo 6 : votre propre serveur MCP. Environ 20 min.

Question : un LLM doit pouvoir interroger mes parties.
À produire : un serveur FastMCP de deux ou trois outils au-dessus de votre API (api.py doit
tourner). Le LLM choisit un outil d'après son nom, sa docstring et ses arguments : soignez-les.
Lancer : uv run python fil_rouge/mcp_server.py   (stdio : c'est le client LLM qui le lance,
voir contexte/README.md pour le brancher). Lancé à la main, il n'affiche rien et attend un
client : c'est normal. Pour tester : npx @modelcontextprotocol/inspector uv run python fil_rouge/mcp_server.py
HTTP public (Render, Cloud Run) : MCP_TRANSPORT=http MCP_TUNNEL=1 python fil_rouge/mcp_server.py
"""

import os
from typing import Literal, Optional

import requests
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

API = os.environ.get("AWP_API_URL", "http://127.0.0.1:8000").rstrip("/")
# Render fournit l'hôte sans schéma quand on référence un autre service : on ajoute https.
if API and not API.startswith(("http://", "https://")):
    API = "https://" + API
# Deux transports. stdio (par défaut) : le client LLM lance ce script lui-même, sur la même machine.
# MCP_TRANSPORT=http : un serveur HTTP sur /mcp, pour un client qui ne lance pas le script (un client
# dans le cloud, via un hébergeur ou un tunnel). En local : 127.0.0.1:8001 (l'API est sur 8000), pas
# ouvert à la salle. Sur un hébergeur qui fixe $PORT (Render, Cloud Run) : 0.0.0.0:$PORT.
HTTP = os.environ.get("MCP_TRANSPORT") == "http"
HOTE = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
# En local, FastMCP refuse un nom d'hôte autre que 127.0.0.1 ou localhost (protection contre le DNS
# rebinding). Derrière un tunnel ou un hébergeur (MCP_TUNNEL=1), l'hôte est public : on lève la
# protection (les outils sont en lecture seule). Sinon, MCP_ALLOWED_HOSTS liste les hôtes acceptés.
TUNNEL = os.environ.get("MCP_TUNNEL") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
if TUNNEL:
    SECU = TransportSecuritySettings(enable_dns_rebinding_protection=False)
elif ALLOWED_HOSTS:
    SECU = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=ALLOWED_HOSTS + ["127.0.0.1:*", "localhost:*"],
        allowed_origins=["*"],
    )
else:
    SECU = None
mcp = FastMCP("echecs", host=HOTE, port=int(os.environ.get("PORT", "8001")), transport_security=SECU)


def _api_get(chemin: str, **params):
    """Appelle l'API (GET) et lève une erreur si la réponse n'est pas un succès."""
    r = requests.get(f"{API}{chemin}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _api_post(chemin: str, payload: dict):
    """Appelle l'API (POST) et lève une erreur si la réponse n'est pas un succès."""
    r = requests.post(f"{API}{chemin}", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def pire_ouvertures(
    cadence: Optional[Literal["bullet", "blitz", "rapid"]] = None,
    min_n: int = 30,
) -> list[dict]:
    """Retourne les familles d'ouvertures où le joueur a le plus faible score moyen (pires d'abord).

    Utiliser cet outil pour répondre à des questions comme « quelles ouvertures me coûtent des points ? »
    ou « quelle est ma pire ouverture en blitz ? ».

    Args:
        cadence: Filtre optionnel de cadence de jeu (bullet, blitz ou rapid). Laisser vide pour toutes.
        min_n: Nombre minimum de parties pour qu'une famille soit incluse (défaut 30).

    Returns:
        Liste de familles avec famille, n (parties), score moyen et gaffes par partie.
    """
    params = {"min_n": min_n}
    if cadence is not None:
        params["cadence"] = cadence
    return _api_get("/ouvertures", **params)


@mcp.tool()
def dernieres_parties(
    cadence: Optional[Literal["aucune", "bullet", "blitz", "rapid", "classical"]] = None,
    couleur: Optional[Literal["white", "black"]] = None,
    limit: int = 10,
) -> list[dict]:
    """Retourne les dernières parties du joueur (les plus récentes d'abord).

    Args:
        cadence: Filtre optionnel de cadence (aucune, bullet, blitz, rapid, classical).
        couleur: Filtre optionnel de couleur jouée (white ou black).
        limit: Nombre maximum de parties à retourner (1-500, défaut 10).
    """
    limit = max(1, min(500, int(limit)))
    params = {"limit": limit}
    if cadence is not None:
        params["cadence"] = cadence
    if couleur is not None:
        params["couleur"] = couleur
    return _api_get("/parties", **params)


@mcp.tool()
def proba_victoire(
    couleur: Literal["white", "black"],
    cadence: Literal["aucune", "bullet", "blitz", "rapid", "classical"],
    ecart_elo: float,
    heure: int,
) -> dict:
    """Estime la probabilité de victoire du joueur dans une situation donnée (modèle fourni).

    Utiliser cet outil pour des questions « et si ? », par exemple jouer avec les noirs,
    à une autre heure, ou avec un certain écart d'Elo.

    Args:
        couleur: Couleur jouée (white ou black).
        cadence: Cadence de la partie (aucune, bullet, blitz, rapid, classical).
        ecart_elo: Elo de l'adversaire moins Elo du joueur (positif = adversaire mieux classé).
        heure: Heure UTC de la partie (0 à 23).

    Returns:
        Dictionnaire contenant proba_victoire (entre 0 et 1).
    """
    heure = max(0, min(23, int(heure)))
    payload = {
        "couleur": couleur,
        "cadence": cadence,
        "ecart_elo": float(ecart_elo),
        "heure": heure,
    }
    return _api_post("/predict", payload)


if __name__ == "__main__":
    # Derrière un tunnel : MCP_TUNNEL=1 MCP_TRANSPORT=http uv run python …, puis npx localtunnel --port 8001
    mcp.run(transport="streamable-http" if HTTP else "stdio")
