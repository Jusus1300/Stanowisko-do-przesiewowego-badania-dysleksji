# Trening modelu ryzyka: regresja logistyczna na cechach z analizy grupowej.
# Wynik (wagi + tabela STATS) nadpisuje model_config.json, z którego korzysta
# analysis_core.calculate_risk_score.

import argparse
import os
import pandas as pd
import numpy as np
import json
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import make_scorer, recall_score

CONFIG_PATH = "model_config.json"

# 1. Wybór danych: ścieżka z linii poleceń (tryb wsadowy) albo okno wyboru pliku.
#    Tkinter importujemy dopiero w tej drugiej gałęzi, żeby tryb wsadowy działał
#    też na maszynie bez środowiska graficznego.
parser = argparse.ArgumentParser(description="Trening modelu ryzyka dysleksji")
parser.add_argument("--input", help="Plik CSV z cechami i kolumną is_dyslexic")
args = parser.parse_args()

file_path = args.input

if not file_path:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # samo okno dialogowe, bez głównego okna Tk

    file_path = filedialog.askopenfilename(
        title="Wybierz plik z danymi do analizy",
        filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
    )

if not file_path:
    print("Nie wybrano pliku. Anulowano działanie programu.")
    exit()

df = pd.read_csv(file_path)
features = ['fix_reg_duration', 'fix_prog_duration', 'fix_reg_std', 'sac_prog_y_stab', 'sac_prog_dist_avg']

missing = [c for c in features + ['is_dyslexic'] if c not in df.columns]
if missing:
    print(f"BŁĄD: w pliku {file_path} brakuje kolumn: {missing}")
    exit(1)

# Rekordy z nieudaną segmentacją mają cechy będące sztucznymi zerami - trenowanie
# na nich przesunęłoby i wagi, i tabelę STATS.
if 'segmentation_failed' in df.columns:
    failed = (df['segmentation_failed'].astype(str).str.strip().str.lower()
              .isin(['true', '1']))
    if failed.any():
        print(f"Pominięto {int(failed.sum())} rekordów z nieudaną segmentacją I2MC.")
        df = df[~failed]

df = df.dropna(subset=features + ['is_dyslexic'])

# Etykieta bywa zapisana jako 0/1 albo jako opis grupy z metadanych zbioru -
# sprowadzamy oba zapisy do 0/1.
DYSLEXIC_TOKENS = {'1', 'true', 'dyslexic', 'dyslexia', 'dys', 'dyslektyk'}
CONTROL_TOKENS = {'0', 'false', 'non-dyslexic', 'nondyslexic', 'control',
                  'kontrola', 'typical', 'healthy'}

def normalize_label(value):
    token = str(value).strip().lower()
    if token in DYSLEXIC_TOKENS:
        return 1
    if token in CONTROL_TOKENS:
        return 0
    return None

labels = df['is_dyslexic'].map(normalize_label)
unknown = df.loc[labels.isna(), 'is_dyslexic'].unique().tolist()
if unknown:
    print(f"BŁĄD: nierozpoznane wartości w kolumnie is_dyslexic: {unknown}")
    exit(1)

df = df.assign(is_dyslexic=labels.astype(int))

X = df[features]
y = df['is_dyslexic']  # 1 = dyslektyk, 0 = grupa kontrolna

print(f"Zbiór treningowy: {len(df)} uczestników "
      f"(dyslektycy={int((y == 1).sum())}, kontrola={int((y == 0).sum())})")

# 2. Standaryzacja i model w jednym Pipeline - scaler dopasowuje się wtedy tylko
#    na foldzie treningowym, bez przecieku danych do walidacji.
scaler = StandardScaler()
# C to odwrotność siły regularyzacji, więc C=inf oznacza jej całkowity brak.
# Zapis równoważny wycofywanemu penalty=None (usuwane w scikit-learn 1.10):
# wagi trafiają wprost do model_config.json, więc nie mogą być ściągnięte karą.
model = LogisticRegression(C=np.inf)
pipeline = Pipeline([('scaler', scaler), ('logreg', model)])

# 3. Kroswalidacja. Czułość to recall klasy 1, swoistość - recall klasy 0.
cv = RepeatedStratifiedKFold(n_splits=7, n_repeats=5, random_state=42)
sensitivity_scorer = make_scorer(recall_score, pos_label=1)
specificity_scorer = make_scorer(recall_score, pos_label=0)

scoring_dict = {
    'accuracy': 'accuracy',
    'sensitivity': sensitivity_scorer,
    'specificity': specificity_scorer
}

# return_estimator=True daje dopasowany pipeline z każdego z 7*5=35 foldów -
# stąd bierzemy współczynniki.
cv_results = cross_validate(
    pipeline, X, y, cv=cv, scoring=scoring_dict, return_estimator=True
)

print(f"Srednia dokladnosc (Accuracy): {cv_results['test_accuracy'].mean():.2f} "
      f"(+/- {cv_results['test_accuracy'].std():.2f})")
print(f"Srednia czulosc (Sensitivity): {cv_results['test_sensitivity'].mean():.2f} "
      f"(+/- {cv_results['test_sensitivity'].std():.2f})")
print(f"Srednia swoistosc (Specificity): {cv_results['test_specificity'].mean():.2f} "
      f"(+/- {cv_results['test_specificity'].std():.2f})")

# 4. Wagi i parametry standaryzacji uśredniamy po foldach zamiast dopasowywać
#    osobny model na całym zbiorze.
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

# 5. Porównanie ze starym modelem - widać, jak zmiany w potoku analizy przełożyły
#    się na wagi i na tabelę STATS.
previous_config = None
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            previous_config = json.load(f)
    except Exception as e:
        print(f"Ostrzeżenie: nie udało się wczytać poprzedniego {CONFIG_PATH} ({e}).")

if previous_config:
    prev_coefs = previous_config.get("weights", {}).get("coefs", [])
    prev_stats = previous_config.get("STATS", {})
    print("\n--- Porównanie z poprzednim model_config.json ---")
    print(f"{'cecha':<22}{'beta (stare)':>14}{'beta (nowe)':>14}"
          f"{'mean (stare)':>15}{'mean (nowe)':>14}{'std (stare)':>14}{'std (nowe)':>13}")
    for i, name in enumerate(features):
        old_b = prev_coefs[i] if i < len(prev_coefs) else float('nan')
        old_m = prev_stats.get(name, {}).get('mean', float('nan'))
        old_s = prev_stats.get(name, {}).get('std', float('nan'))
        print(f"{name:<22}{old_b:>14.4f}{coefs[i]:>14.4f}"
              f"{old_m:>15.4f}{feature_means[i]:>14.4f}{old_s:>14.4f}{feature_stds[i]:>13.4f}")
    old_i = previous_config.get("weights", {}).get("intercept", float('nan'))
    print(f"{'intercept':<22}{old_i:>14.4f}{intercept:>14.4f}")

# 6. Zapis konfiguracji. float()/tolist() zamieniają typy numpy na standardowe,
#    inaczej json.dump ich nie zserializuje.
model_config = {
    "weights": {
        "intercept": float(intercept),
        "coefs": coefs.tolist()
    },
    "STATS": {}
}

for name, mean, std in zip(features, feature_means, feature_stds):
    model_config["STATS"][name] = {'mean': float(mean), 'std': float(std)}

with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(model_config, f, indent=4)

print(f"\nPomyślnie zapisano tabelę STATS oraz wagi modelu do pliku '{CONFIG_PATH}'.")
