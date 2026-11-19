"""Facultatif. model.joblib est déjà fourni dans fil_rouge/ : pas besoin de lancer ce fichier
pour le bonus /predict de l'exo 5. Il montre comment ce modèle a été entraîné.

Question : avec quelle couleur, à quelle cadence, à quelle heure ce joueur gagne-t-il le plus ?
À produire : un modèle de classification scikit-learn, son erreur mesurée par validation croisée,
une référence à battre (toujours prédire la fréquence de victoire), et model.joblib enregistré
à côté de ce fichier (il remplace celui fourni).
Lancer : uv run python fil_rouge/train.py
"""

from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data import load_data

df = load_data().copy()

# 1. Variables explicatives et cible
features = ["couleur", "cadence", "ecart_elo", "heure"]
target = "victoire"

df[target] = (df["resultat"] == "victoire").astype(int)

# ecart_elo peut être manquant : on impute simplement par la médiane pour l'entraînement
if df["ecart_elo"].isna().any():
    df["ecart_elo"] = df["ecart_elo"].fillna(df["ecart_elo"].median())

X = df[features]
y = df[target]

# 2. Pipeline : encodage des catégories + mise à l'échelle, puis modèle
preprocess = ColumnTransformer(
    transformers=[
        ("onehotencoder", OneHotEncoder(handle_unknown="ignore"), ["couleur", "cadence", "heure"]),
        ("standardscaler", StandardScaler(), ["ecart_elo"]),
    ]
)

model = Pipeline(
    steps=[
        ("columntransformer", preprocess),
        ("logisticregression", LogisticRegression(max_iter=1000)),
    ]
)

# 3. Validation croisée et référence à battre
cv = 5
scores_model = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
baseline = DummyClassifier(strategy="most_frequent")
scores_baseline = cross_val_score(baseline, X, y, cv=cv, scoring="accuracy")

print(f"Modèle (accuracy CV, {cv} folds)    : {scores_model.mean():.3f} ± {scores_model.std():.3f}")
print(f"Référence 'classe majoritaire' (CV) : {scores_baseline.mean():.3f} ± {scores_baseline.std():.3f}")
print(f"Gain moyen                          : {scores_model.mean() - scores_baseline.mean():+.3f}")

# 4. Entraînement final et sauvegarde à côté de ce fichier
model.fit(X, y)
out_path = Path(__file__).resolve().parent / "model.joblib"
joblib.dump(model, out_path)
print(f"Modèle enregistré dans : {out_path}")
