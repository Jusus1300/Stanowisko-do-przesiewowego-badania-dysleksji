import tkinter as tk
import pandas as pd
import numpy as np
import json
from tkinter import filedialog
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate
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

# 2. Standaryzacja (z-score)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 3. Definicja poprawnego modelu
model = LogisticRegression(penalty=None) # czysta regresja logistyczna bez regularyzacji

# 4. Poprawna walidacja (Kroswalidacja)
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

# Realne uruchomienie kroswalidacji
cv_results = cross_validate(model, X_scaled, y, cv=cv, scoring=scoring_dict)

# Wyświetlenie uśrednionych wyników z walidacji
print(f"Srednia dokladnosc (Accuracy): {cv_results['test_accuracy'].mean():.2f}")
print(f"Srednia czulosc (Sensitivity): {cv_results['test_sensitivity'].mean():.2f}")
print(f"Srednia swoistosc (Specificity): {cv_results['test_specificity'].mean():.2f}")

# 5. Dopasowanie modelu na CAŁOŚCI, żeby wyciągnąć oficjalne wagi do wzoru (3.1)
model.fit(X_scaled, y)

print(f"Wyraz wolny (beta_0): {model.intercept_[0]}")
print(f"Wspolczynniki (beta_1 do beta_5): {model.coef_[0]}")

# 6. Tworzymy słownik z konfiguracją (zmieniamy typy numpy na standardowe typy Python za pomocą float() i tolist())
model_config = {
    "weights": {
        "intercept": float(model.intercept_[0]),
        "coefs": model.coef_[0].tolist()
    },
    "STATS": {}
}

# Wypełniamy tabelę STATS
for name, mean, std in zip(features, scaler.mean_, np.sqrt(scaler.var_)):
    model_config["STATS"][name] = {'mean': float(mean), 'std': float(std)}

# Zapisujemy do pliku tekstowego "model_config.json"
with open("model_config.json", "w", encoding="utf-8") as f:
    json.dump(model_config, f, indent=4)

print("\nPomyślnie zapisano tabelę STATS oraz wagi modelu do pliku 'model_config.json'.")