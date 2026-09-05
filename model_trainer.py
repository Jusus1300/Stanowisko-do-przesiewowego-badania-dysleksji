import tkinter as tk
import pandas as pd
import numpy as np
import json
from tkinter import filedialog
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import make_scorer, recall_score

# 1. Wybór i wczytanie danych przez okno eksploratora
root = tk.Tk()
root.withdraw()  # Ukrywa główne okienko aplikacji Tkinter

file_path = filedialog.askopenfilename(
    title="Wybierz plik z danymi do analizy",
    filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
)

if not file_path:
    print("Nie wybrano pliku. Anulowano działanie programu.")
    exit()

df = pd.read_csv(file_path)
features = ['fix_reg_duration', 'fix_prog_duration', 'fix_reg_std', 'sac_prog_y_stab', 'sac_prog_dist_avg']

X = df[features]
y = df['is_dyslexic'] # 1 dla dyslektyka, 0 dla kontrolnej

# 2. Standaryzacja (z-score) + model w jednym Pipeline, żeby scaler był dopasowywany
#    wyłącznie na foldzie treningowym w każdej iteracji CV (bez przecieku danych)
scaler = StandardScaler()
model = LogisticRegression(penalty=None) # czysta regresja logistyczna bez regularyzacji
pipeline = Pipeline([('scaler', scaler), ('logreg', model)])

# 3. Poprawna walidacja (Kroswalidacja)
cv = RepeatedStratifiedKFold(n_splits=7, n_repeats=5, random_state=42)
# Czułość (Sensitivity) to czułość dla klasy pozytywnej (1)
sensitivity_scorer = make_scorer(recall_score, pos_label=1)
# Swoistość (Specificity) to czułość dla klasy negatywnej (0)
specificity_scorer = make_scorer(recall_score, pos_label=0)

# Poprawny słownik metryk
scoring_dict = {
    'accuracy': 'accuracy',
    'sensitivity': sensitivity_scorer,
    'specificity': specificity_scorer
}

# Realne uruchomienie kroswalidacji; return_estimator=True zwraca dopasowany
# pipeline (scaler + model) z każdego z 7*5=35 foldów, z których wyciągamy
# współczynniki, żeby estymacja wag rzeczywiście pochodziła z kroswalidacji
cv_results = cross_validate(
    pipeline, X, y, cv=cv, scoring=scoring_dict, return_estimator=True
)

# Wyświetlenie uśrednionych wyników z walidacji
print(f"Srednia dokladnosc (Accuracy): {cv_results['test_accuracy'].mean():.2f}")
print(f"Srednia czulosc (Sensitivity): {cv_results['test_sensitivity'].mean():.2f}")
print(f"Srednia swoistosc (Specificity): {cv_results['test_specificity'].mean():.2f}")

# 4. Estymacja współczynników z procedury kroswalidacji: uśredniamy wagi
#    (wyraz wolny, współczynniki) oraz parametry standaryzacji ze wszystkich
#    foldów zamiast dopasowywać osobny model na całym zbiorze
fold_intercepts = np.array([est.named_steps['logreg'].intercept_[0] for est in cv_results['estimator']])
fold_coefs = np.array([est.named_steps['logreg'].coef_[0] for est in cv_results['estimator']])
fold_means = np.array([est.named_steps['scaler'].mean_ for est in cv_results['estimator']])
fold_stds = np.array([np.sqrt(est.named_steps['scaler'].var_) for est in cv_results['estimator']])

intercept = fold_intercepts.mean()
coefs = fold_coefs.mean(axis=0)
feature_means = fold_means.mean(axis=0)
feature_stds = fold_stds.mean(axis=0)

print(f"Wyraz wolny (beta_0): {intercept}")
print(f"Wspolczynniki (beta_1 do beta_5): {coefs}")

# 5. Tworzymy słownik z konfiguracją (zmieniamy typy numpy na standardowe typy Python za pomocą float() i tolist())
model_config = {
    "weights": {
        "intercept": float(intercept),
        "coefs": coefs.tolist()
    },
    "STATS": {}
}

# Wypełniamy tabelę STATS (średnie i odchylenia uśrednione z foldów treningowych CV)
for name, mean, std in zip(features, feature_means, feature_stds):
    model_config["STATS"][name] = {'mean': float(mean), 'std': float(std)}

# Zapisujemy do pliku tekstowego "model_config.json"
with open("model_config.json", "w", encoding="utf-8") as f:
    json.dump(model_config, f, indent=4)

print("\nPomyślnie zapisano tabelę STATS oraz wagi modelu do pliku 'model_config.json'.")