"""Compatibilité : l'ancien point d'entrée de l'exo 2 ouvre la page du serveur unifié.

Le serveur unique est ``fil_rouge/app.py`` (port 8501). Ce fichier reste pour ne
pas casser les commandes existantes : il exécute la même page sur le port 8502.
"""

import os
import runpy
import sys

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)

from single_instance import bootstrap_streamlit_app

bootstrap_streamlit_app(__file__, port=8502)

# La page appelée n'est pas dans le serveur unifié : elle pose elle-même sa config.
os.environ.pop("AWP_UNIFIED", None)

runpy.run_path(
    os.path.join(RACINE, "pages", "02_Exo2_Appli_hebdo.py"),
    run_name="__main__",
)
