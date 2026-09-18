"""
Prosty skrypt dopisujący kolumnę is_dyslexic (1/0) do pliku z wynikami grupowymi.

Etykiety pobierane są z pliku dyslexia_class_label.csv (kolumny: subject_id, class_id, label).
Identyfikator uczestnika wyciągany jest z kolumny 'filename' (np. Subject_1003_T4_..._raw.csv -> 1003).

Użycie:
    python dodaj_etykiety.py wyniki_grupowe.csv dyslexia_class_label.csv [plik_wyjsciowy.csv]
"""

import os
import re
import sys
import pandas as pd


def wczytaj_etykiety(sciezka_etykiet):
    # Zwraca mapę {subject_id: 0/1}. Preferujemy class_id, a gdy go brak -
    # tekstową kolumnę label.
    df = pd.read_csv(sciezka_etykiet)

    if 'class_id' in df.columns:
        etykiety = pd.to_numeric(df['class_id'], errors='coerce')
    else:
        etykiety = df['label'].astype(str).str.strip().str.lower().eq('dyslexic').astype(int)

    return dict(zip(pd.to_numeric(df['subject_id'], errors='coerce'), etykiety))


def wyciagnij_id(filename):
    # 'Subject_1003_T4_..._raw.csv' -> 1003
    dopasowanie = re.search(r'(\d+)', str(filename))
    return int(dopasowanie.group(1)) if dopasowanie else None


def dodaj_etykiety(sciezka_wynikow, sciezka_etykiet, sciezka_wyjsciowa=None):
    mapa = wczytaj_etykiety(sciezka_etykiet)
    df = pd.read_csv(sciezka_wynikow)

    if 'filename' not in df.columns:
        raise ValueError("Plik z wynikami nie zawiera kolumny 'filename'.")

    ids = df['filename'].apply(wyciagnij_id)
    df['is_dyslexic'] = ids.map(mapa).astype('Int64')

    # Brak etykiety nie przerywa zapisu, ale musi być widoczny - te wiersze
    # odpadną potem w model_trainer.py.
    brakujace = df.loc[df['is_dyslexic'].isna(), 'filename'].tolist()
    if brakujace:
        print(f"UWAGA: brak etykiety dla {len(brakujace)} uczestników:")
        for nazwa in brakujace:
            print(f"  - {nazwa}")

    # Bez podanej ścieżki nadpisujemy plik wejściowy.
    if sciezka_wyjsciowa is None:
        sciezka_wyjsciowa = sciezka_wynikow

    df.to_csv(sciezka_wyjsciowa, index=False)

    liczba_dyslektykow = int((df['is_dyslexic'] == 1).sum())
    liczba_kontroli = int((df['is_dyslexic'] == 0).sum())
    print(f"Zapisano: {sciezka_wyjsciowa}")
    print(f"Dyslektycy: {liczba_dyslektykow} | Grupa kontrolna: {liczba_kontroli} | Bez etykiety: {len(brakujace)}")

    return df


def main():
    if len(sys.argv) < 3:
        print(__doc__)  # docstring modułu służy tu za instrukcję użycia
        sys.exit(1)

    sciezka_wynikow = sys.argv[1]
    sciezka_etykiet = sys.argv[2]
    sciezka_wyjsciowa = sys.argv[3] if len(sys.argv) > 3 else None

    for sciezka in (sciezka_wynikow, sciezka_etykiet):
        if not os.path.exists(sciezka):
            print(f"Nie znaleziono pliku: {sciezka}")
            sys.exit(1)

    dodaj_etykiety(sciezka_wynikow, sciezka_etykiet, sciezka_wyjsciowa)


if __name__ == '__main__':
    main()
