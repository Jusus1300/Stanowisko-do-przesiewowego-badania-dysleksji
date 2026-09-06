"""
Skrypt weryfikacyjny do recenzji pracy dyplomowej (RECENZJA_PRACY.md).

Odtwarza obliczeniowo ustalenia K1, K2 i K4:
  * K1 - metryki skutecznosci raportowane w Tab. 5.1 pracy,
  * K2 - wagi modelu z rownania (3.2) na tle historii repozytorium,
  * K4 - kierunek efektu i stabilnosc wspolczynnikow dla cech x3 i x5.

Zbior cech z etykietami (wyniki_grupowe_etdd70_meaningful_text.csv) zostal usuniety
z repozytorium w commicie 859dafc; skrypt odzyskuje go z historii git, wiec nie trzeba
go przywracac do drzewa roboczego.

Uruchomienie (z katalogu glownego repozytorium):
    python recenzja/weryfikacja_wynikow.py
"""

import io
import json
import subprocess
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (RepeatedStratifiedKFold, StratifiedKFold,
                                     cross_val_predict, cross_validate)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, make_scorer, recall_score

FEATURES = ['fix_reg_duration', 'fix_prog_duration', 'fix_reg_std',
            'sac_prog_y_stab', 'sac_prog_dist_avg']

DATASET_BLOB = '859dafc^:wyniki_grupowe_etdd70_meaningful_text.csv'

# Trzy stany model_config.json w historii repozytorium.
CONFIG_COMMITS = [
    ('ad66f15', 'pierwszy commit'),
    ('bd60e47', 'ODPOWIADA ROWNANIU (3.2) W PRACY'),
    ('8b730cd', 'stan HEAD repozytorium'),
]


def git_show(ref):
    out = subprocess.run(['git', 'show', ref], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"Nie udalo sie odczytac {ref} z historii git:\n{out.stderr}")
    return out.stdout


def make_pipeline():
    # Dokladnie taki sam potok jak w model_trainer.py (regularyzacja wylaczona).
    return Pipeline([('scaler', StandardScaler()),
                     ('logreg', LogisticRegression(C=np.inf))])


def naglowek(tekst):
    print(f"\n{'=' * 78}\n{tekst}\n{'=' * 78}")


def main():
    df = pd.read_csv(io.StringIO(git_show(DATASET_BLOB)))
    X = df[FEATURES]
    y = (df['is_dyslexic'] == 'dyslexic').astype(int)
    print(f"Zbior odzyskany z historii git: {len(df)} uczestnikow "
          f"(dyslektycy={int(y.sum())}, kontrola={int((1 - y).sum())})")

    cv = RepeatedStratifiedKFold(n_splits=7, n_repeats=5, random_state=42)

    # ------------------------------------------------------------------ K1
    naglowek("K1 - metryki skutecznosci (praca podaje 80,0% / 80,0% / 80,0%)")
    res = cross_validate(
        make_pipeline(), X, y, cv=cv,
        scoring={'acc': 'accuracy',
                 'sens': make_scorer(recall_score, pos_label=1),
                 'spec': make_scorer(recall_score, pos_label=0)},
        return_estimator=True)
    print("Powtarzana kroswalidacja 7x5, ziarno 42 (jak w model_trainer.py):")
    for etykieta, klucz in [('dokladnosc', 'acc'), ('czulosc', 'sens'), ('swoistosc', 'spec')]:
        v = res[f'test_{klucz}']
        print(f"  {etykieta:<12} {v.mean():.3f} +/- {v.std():.3f}")

    print("\nMacierze pomylek dla wariantow alternatywnych "
          "(praca podaje TP=28 FN=7 FP=7 TN=28):")
    for opis, splitter in [
        ('out-of-fold, StratifiedKFold(7) bez mieszania', StratifiedKFold(7)),
        ('out-of-fold, StratifiedKFold(7) shuffle=42',
         StratifiedKFold(7, shuffle=True, random_state=42)),
    ]:
        pred = cross_val_predict(make_pipeline(), X, y, cv=splitter)
        tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
        print(f"  {opis:<46} TP={tp:2d} FN={fn:2d} FP={fp:2d} TN={tn:2d}")

    # ------------------------------------------------------------------ K2
    naglowek("K2 - wagi modelu: praca vs. historia repozytorium")
    intercept = np.mean([e.named_steps['logreg'].intercept_[0] for e in res['estimator']])
    coefs = np.mean([e.named_steps['logreg'].coef_[0] for e in res['estimator']], axis=0)
    print(f"{'zrodlo':<38}{'b0':>8}" + ''.join(f"{'b' + str(i + 1):>9}" for i in range(5)))
    print(f"{'odtworzone z tego zbioru':<38}{intercept:>8.3f}"
          + ''.join(f"{c:>9.3f}" for c in coefs))
    print(f"{'praca, rownanie (3.2)':<38}{0.272:>8.3f}"
          + ''.join(f"{c:>9.3f}" for c in [1.707, 1.041, -0.329, 0.764, -0.165]))
    for ref, opis in CONFIG_COMMITS:
        cfg = json.loads(git_show(f'{ref}:model_config.json'))
        print(f"{ref + ' (' + opis + ')':<38}{cfg['weights']['intercept']:>8.3f}"
              + ''.join(f"{c:>9.3f}" for c in cfg['weights']['coefs']))

    # ------------------------------------------------------------------ K4
    naglowek("K4 - kierunek efektu i stabilnosc wspolczynnikow")
    fold_coefs = np.array([e.named_steps['logreg'].coef_[0] for e in res['estimator']])
    print("Kierunek jednowymiarowy (srednie w grupach) vs. znak wagi w modelu:\n")
    print(f"{'cecha':<20}{'kontrola':>10}{'dyslektycy':>12}{'kierunek':>16}"
          f"{'beta':>9}{'std(beta)':>11}{'znak +':>9}")
    for i, f in enumerate(FEATURES):
        a, b = df.loc[y == 0, f], df.loc[y == 1, f]
        kier = 'wyzsze u dys.' if b.mean() > a.mean() else 'nizsze u dys.'
        c = fold_coefs[:, i]
        print(f"{f:<20}{a.mean():>10.3f}{b.mean():>12.3f}{kier:>16}"
              f"{c.mean():>9.3f}{c.std():>11.3f}{100 * (c > 0).mean():>8.0f}%")

    print("\nMacierz korelacji cech (zrodlo niestabilnosci wag):")
    print(X.corr().round(2).to_string())
    print("\nUwaga: fix_reg_std jest WYZSZE u dyslektykow (kierunek dodatni),"
          "\nmimo ujemnego wspolczynnika w modelu wielowymiarowym - efekt supresora"
          "\nprzy korelacji 0,86 z fix_reg_duration. Zob. K4 w RECENZJA_PRACY.md.")


if __name__ == '__main__':
    main()
