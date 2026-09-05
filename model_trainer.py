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

# 1. Wybór i wczytanie danych: ścieżka z linii poleceń (tryb wsadowy, np.
#    retrening na gotowym pliku wyników analizy grupowej) albo okno
#    eksploratora, gdy skrypt jest odpalany ręcznie przez operatora.
#    Tkinter jest importowany dopiero w gałęzi z oknem - dzięki temu tryb
#    wsadowy działa też na maszynie bez środowiska graficznego.
parser = argparse.ArgumentParser(description="Trening modelu ryzyka dysleksji")
parser.add_argument("--input", help="Plik CSV z cechami i kolumną is_dyslexic")
args = parser.parse_args()

file_path = args.input

if not file_path:
    import tkinter as tk
    from tkinter import filedialog

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

missing = [c for c in features + ['is_dyslexic'] if c not in df.columns]
if missing:
    print(f"BŁĄD: w pliku {file_path} brakuje kolumn: {missing}")
    exit(1)

# Wiersze z nieudaną segmentacją I2MC mają cechy będące sztucznymi zerami
# (analysis_core.calculate_features ustawia wtedy segmentation_failed=True).
# Trenowanie na nich przesunęłoby zarówno wagi, jak i tabelę STATS, więc
# odrzucamy je jawnie zamiast wpuszczać jako "pomiar zerowy".
if 'segmentation_failed' in df.columns:
    failed = (df['segmentation_failed'].astype(str).str.strip().str.lower()
              .isin(['true', '1']))
    if failed.any():
        print(f"Pominięto {int(failed.sum())} rekordów z nieudaną segmentacją I2MC.")
        df = df[~failed]

df = df.dropna(subset=features + ['is_dyslexic'])

# Etykieta może przyjść jako 0/1 albo jako opis grupy z metadanych zbioru
# (np. 'dyslexic' / 'non-dyslexic' w ETDD70) - normalizujemy oba zapisy do 0/1.
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
y = df['is_dyslexic']  # 1 dla dyslektyka, 0 dla kontrolnej

print(f"Zbiór treningowy: {len(df)} uczestników "
      f"(dyslektycy={int((y == 1).sum())}, kontrola={int((y == 0).sum())})")

# 2. Standaryzacja (z-score) + model w jednym Pipeline, żeby scaler był dopasowywany
#    wyłącznie na foldzie treningowym w każdej iteracji CV (bez przecieku danych)
scaler = StandardScaler()
model = LogisticRegression(C=np.inf) # czysta regresja logistyczna bez regularyzacji
# C to odwrotnosc sily regularyzacji, wiec C=np.inf oznacza jej calkowity brak.
# Zapis rownowazny wycofywanemu penalty=None (usuwane w scikit-learn 1.10),
# dajacy identyczne wspolczynniki - wagi trafiaja wprost do model_config.json,
# wiec nie moga byc sciagniete przez zadna kare.
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

# Wyświetlenie uśrednionych wyników z walidacji (ze zmiennością między foldami)
print(f"Srednia dokladnosc (Accuracy): {cv_results['test_accuracy'].mean():.2f} "
      f"(+/- {cv_results['test_accuracy'].std():.2f})")
print(f"Srednia czulosc (Sensitivity): {cv_results['test_sensitivity'].mean():.2f} "
      f"(+/- {cv_results['test_sensitivity'].std():.2f})")
print(f"Srednia swoistosc (Specificity): {cv_results['test_specificity'].mean():.2f} "
      f"(+/- {cv_results['test_specificity'].std():.2f})")

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

# 5. Porównanie z poprzednią wersją modelu, żeby było widać, jak zmiany w
#    potoku analizy przełożyły się na wagi i na tabelę STATS
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

# 6. Tworzymy słownik z konfiguracją (zmieniamy typy numpy na standardowe typy Python za pomocą float() i tolist())
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
with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(model_config, f, indent=4)

print(f"\nPomyślnie zapisano tabelę STATS oraz wagi modelu do pliku '{CONFIG_PATH}'.")
