# streamlitchecs

[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=Emanrhesus-positif/streamlitchecs&branch=main&mainModule=fil_rouge/app.py)

Tableau de bord Streamlit pour répondre à une question simple : **où ce joueur
d'échecs perd-il des points, et que devrait-il travailler ?**

Les données sont un export ChessXP anonymisé (3 023 parties, 2023 → 2026) :
`data/echecs/`.

## Application en ligne

Déployée sur Streamlit Community Cloud :

<!-- Remplacez par l'URL donnée par Streamlit Cloud -->
`https://streamlitchecs.streamlit.app` (à confirmer après le déploiement)

## Pages

| Page | Contenu |
| --- | --- |
| **Analyse** | Score par famille d'ouvertures, gaffes par phase, score selon l'heure UTC, réponse calculée, simulateur |
| **Appli hebdo** | Filtres cadence / période / couleur / seuil, indicateurs, figures filtrées avec sélection, simulateur |
| **Drill-down** | Clic sur une famille → parties → coups jugés mauvais |
| **API & modèle** | Client de l'API FastAPI (`/ouvertures`, `/parties`, `/predict`) |
| **Outils MCP** | Console des trois outils exposés au LLM |

Le simulateur rejoue les **moments critiques** (position avant le coup + coup
fautif + meilleur coup) : Précédent / Suivant / Jouer / Tout lire, avec une
animation pas à pas dans un composant HTML/JS, sans relance Streamlit.

## Lancer en local

```powershell
python -m pip install -r requirements.txt
python -m streamlit run fil_rouge/app.py
```

→ <http://127.0.0.1:8501>

## API, Dash et MCP (en local)

L'API et le serveur MCP ne sont pas déployés sur Streamlit Community Cloud : les
pages correspondantes affichent les commandes à lancer.

```powershell
# API FastAPI (port 8000)
python -m uvicorn api:app --app-dir fil_rouge --host 127.0.0.1 --port 8000

# Drill-down Dash (port 8050)
python fil_rouge/app_dash.py

# Serveur MCP (stdio)
python fil_rouge/mcp_server.py
claude mcp add --transport stdio echecs -- python fil_rouge/mcp_server.py
```

## Tests

```powershell
python -m pytest -q
```

Les tests couvrent les données, l'API (paramètres valides et erreurs 422) et le
chargement des pages Streamlit via `streamlit.testing.v1.AppTest`.

## Déploiement Streamlit Cloud

1. Pousser ce dépôt sur GitHub.
2. Sur <https://share.streamlit.io> : **Create app** → dépôt `streamlitchecs`,
   branche `main`, fichier principal `fil_rouge/app.py`.
3. Le thème sombre est déjà dans `.streamlit/config.toml` ; aucune variable
   d'environnement n'est nécessaire.

## Structure

```
fil_rouge/
  app.py               # entrée unique (st.navigation)
  01_figures.py        # page Analyse
  pages/               # Appli hebdo, Drill-down, API, Outils MCP
  data.py              # chargement / validation des CSV
  ui.py                # thème sombre partagé
  chess_sim.py         # simulateur d'échiquier HTML/JS
  api.py               # FastAPI
  app_dash.py          # équivalent Dash du drill-down
  mcp_server.py        # serveur MCP
  model.joblib         # modèle logistique pour /predict
data/echecs/           # CSV + documentation des colonnes
tests/                 # pytest (données, API, pages)
```
