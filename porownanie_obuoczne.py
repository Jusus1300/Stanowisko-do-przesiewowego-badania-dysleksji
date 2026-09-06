"""Porównanie wariantów segmentacji I2MC na danych obuocznych ETDD70.

Skrypt pomocniczy (nie wchodzi w skład potoku diagnostycznego). Służy do
zmierzenia, jak na wyniki końcowe wpływa to, który sygnał trafia do kanałów
wejściowych I2MC. Porównywane są cztery warianty:

  dup     - wariant historyczny (sprzed przejścia na obuoczność): sygnał oka
            lewego wpisany do obu kanałów ('L_X' i 'R_X' to ta sama tablica),
  mono    - uczciwie jednooczny: do I2MC trafia wyłącznie 'L_X'/'L_Y',
  mono_r  - jak wyżej, ale na oku prawym (kontrola arbitralności wyboru oka),
  bino    - rzeczywiście obuoczny: 'L_*' z oka lewego, 'R_*' z oka prawego.
            To wariant, na którym pracuje obecny potok.

Klastrowanie 2-means wewnątrz I2MC startuje z losowej inicjalizacji (kmeans++
w I2MC.kmeans2 woła np.random bez ustawionego ziarna), więc pojedynczy przebieg
nie rozstrzyga niczego. Każdy wariant jest liczony dla N_REP ziaren, a efekt
systematyczny raportowany jest na tle rozrzutu międzyziarnowego.

Użycie:
    python porownanie_obuoczne.py --dane KATALOG [--powtorzenia 12] [--wyjscie plik.csv]

KATALOG ma zawierać pliki 'Subject_*_raw.csv' zbioru ETDD70 (kolumny
gaze_x_left, gaze_y_left, gaze_x_right, gaze_y_right, time).
"""

import argparse
import concurrent.futures as futures
import os
import warnings

import numpy as np
import pandas as pd
import I2MC

import analysis_core as core

WARIANTY = ('dup', 'mono', 'mono_r', 'bino')
CECHY_MODELU = ['fix_reg_duration', 'fix_prog_duration', 'fix_reg_std',
                'sac_prog_y_stab', 'sac_prog_dist_avg']


def zbuduj_opcje(sample_rate_ms):
    # Identyczna konfiguracja jak w analysis_core.apply_i2mc_segmentation -
    # porównywany jest wyłącznie dobór sygnału wejściowego, nie parametry.
    freq_nominal = round(1000.0 / sample_rate_ms)
    downsamples = [d for d in (2, 5, 10) if freq_nominal % d == 0] or [1]
    return {
        'xres': core.SCREEN_WIDTH,
        'yres': core.SCREEN_HEIGHT,
        'freq': freq_nominal,
        'missingx': np.nan,
        'missingy': np.nan,
        'windowtimeInterp': core.INTERP_MAX_GAP_MS / 1000.0,
        'maxdisp': core.SCREEN_WIDTH * 0.2 * np.sqrt(2),
        'windowtime': core.WINDOW_SIZE_MS / 1000.0,
        'steptime': 0.02,
        'downsamples': downsamples,
        'chebyOrder': 8,
        'maxerrors': 100,
        'cutoffstd': 2.0,
    }


def wczytaj(sciezka):
    # Ten sam filtr poprawności co w analysis_group.process_single_subject,
    # ale stosowany osobno do każdego oka: próbka odrzucona na jednym oku nie
    # unieważnia drugiego, bo I2MC potrafi korzystać z oka pozostałego.
    df = pd.read_csv(sciezka)
    dane = pd.DataFrame()
    dane['x'] = df['gaze_x_left'].astype(float)
    dane['y'] = df['gaze_y_left'].astype(float)
    dane['x_prawe'] = df['gaze_x_right'].astype(float)
    dane['y_prawe'] = df['gaze_y_right'].astype(float)

    if 'time' in df.columns:
        sample_rate_ms = core.estimate_sample_rate_ms(df['time'], core.GROUP_EXPERIMENT_FREQ)
    else:
        sample_rate_ms = 1000.0 / core.GROUP_EXPERIMENT_FREQ

    bledne_l = ~((dane['x'] > 1) & (dane['y'] > 1))
    bledne_p = ~((dane['x_prawe'] > 1) & (dane['y_prawe'] > 1))
    dane.loc[bledne_l, ['x', 'y']] = np.nan
    dane.loc[bledne_p, ['x_prawe', 'y_prawe']] = np.nan

    return dane, sample_rate_ms


def _kolumna(dane, nazwa):
    wartosci = dane[nazwa].values.astype(float)
    return np.where(np.isfinite(wartosci), wartosci, np.nan)


def segmentuj(dane, sample_rate_ms, wariant):
    czas = dane.index.values * sample_rate_ms
    lewe_x, lewe_y = _kolumna(dane, 'x'), _kolumna(dane, 'y')
    prawe_x, prawe_y = _kolumna(dane, 'x_prawe'), _kolumna(dane, 'y_prawe')

    if wariant == 'dup':
        wejscie = {'time': czas, 'L_X': lewe_x, 'L_Y': lewe_y,
                   'R_X': lewe_x, 'R_Y': lewe_y}
    elif wariant == 'mono':
        wejscie = {'time': czas, 'L_X': lewe_x, 'L_Y': lewe_y}
    elif wariant == 'mono_r':
        wejscie = {'time': czas, 'L_X': prawe_x, 'L_Y': prawe_y}
    elif wariant == 'bino':
        wejscie = {'time': czas, 'L_X': lewe_x, 'L_Y': lewe_y,
                   'R_X': prawe_x, 'R_Y': prawe_y}
    else:
        raise ValueError(f"nieznany wariant: {wariant}")

    wynik = I2MC.I2MC(wejscie, zbuduj_opcje(sample_rate_ms), logging=False)
    return _wyluskaj_fiksacje(wynik)


def _wyluskaj_fiksacje(wynik):
    # Ta sama obsługa formatów zwracanych przez I2MC co w analysis_core.
    if isinstance(wynik, tuple):
        for element in wynik:
            if isinstance(element, pd.DataFrame):
                kolumny = element.columns.tolist()
                if any(k in kolumny for k in ('xpos', 'Xpos', 'mean_x')) and \
                   any(k in kolumny for k in ('dur', 'duration', 'dur_ms')):
                    return element
            elif isinstance(element, dict):
                if 'final_fixations' in element:
                    return pd.DataFrame(element['final_fixations'])
                if any(k in element for k in ('xpos', 'Xpos', 'mean_x')) and \
                   any(k in element for k in ('dur', 'duration', 'dur_ms')):
                    return pd.DataFrame(element)
    elif isinstance(wynik, dict) and 'final_fixations' in wynik:
        return pd.DataFrame(wynik['final_fixations'])
    return pd.DataFrame()


def zadanie(argumenty):
    sciezka, wariant, powtorzenie = argumenty
    warnings.filterwarnings("ignore")
    dane, sample_rate_ms = wczytaj(sciezka)

    # Ziarno ustawiane jawnie, żeby porównanie wariantów było powtarzalne:
    # ten sam numer powtórzenia oznacza ten sam stan generatora dla każdego
    # wariantu, więc różnice między wariantami nie biorą się z losowania.
    np.random.seed(1000 * powtorzenie + 7)

    fiksacje = segmentuj(dane, sample_rate_ms, wariant)
    zdarzenia = core.classify_movements(fiksacje, sample_rate_ms)
    cechy = core.calculate_features(zdarzenia, sample_rate_ms)
    diagnoza = core.calculate_risk_score(cechy)

    return {
        'plik': os.path.basename(sciezka),
        'wariant': wariant,
        'powtorzenie': powtorzenie,
        'liczba_fiksacji': len(fiksacje),
        'score': diagnoza['total_score'],
        **{k: v for k, v in cechy.items() if k != 'segmentation_failed'},
    }


def raport(wyniki):
    srednie = wyniki.pivot_table(index='plik', columns='wariant', values='score', aggfunc='mean')
    odchylenia = wyniki.pivot_table(index='plik', columns='wariant', values='score', aggfunc='std')
    kolejnosc = [w for w in WARIANTY if w in srednie.columns]
    srednie = srednie[kolejnosc]

    print("\n=== Średni wynik modelu (score) z powtórzeń ===")
    print(srednie.round(3).to_string())

    print("\n=== Odchylenie standardowe między ziarnami RNG ===")
    print(odchylenia[kolejnosc].round(4).to_string())

    print("\n=== Wielkość efektów (średnia z wartości bezwzględnych) ===")
    szum = odchylenia[kolejnosc].mean().mean()
    if {'dup', 'mono'} <= set(srednie.columns):
        d = (srednie['dup'] - srednie['mono'])
        print(f"  duplikacja oka lewego (dup - mono):  {d.abs().mean():.4f}  (max {d.abs().max():.4f})")
    if {'mono', 'mono_r'} <= set(srednie.columns):
        d = (srednie['mono'] - srednie['mono_r'])
        print(f"  wybór oka (lewe vs prawe):           {d.abs().mean():.4f}  (max {d.abs().max():.4f})")
    if {'bino', 'dup'} <= set(srednie.columns):
        d = (srednie['bino'] - srednie['dup'])
        print(f"  przejście na obuoczne (bino - dup):  {d.abs().mean():.4f}  (max {d.abs().max():.4f}), "
              f"kierunek {d.mean():+.4f}")
    print(f"  rozrzut losowy k-means (średnie SD): {szum:.4f}")

    print("\n=== Przesunięcie cech modelu przy przejściu na obuoczne ===")
    print("    (w jednostkach populacyjnego odchylenia z model_config.json)")
    if {'bino', 'dup'} <= set(wyniki['wariant'].unique()):
        cechy = wyniki.pivot_table(index='plik', columns='wariant', values=CECHY_MODELU, aggfunc='mean')
        statystyki = _statystyki_populacyjne()
        for nazwa in CECHY_MODELU:
            delta = (cechy[(nazwa, 'bino')] - cechy[(nazwa, 'dup')]).abs() / statystyki[nazwa]['std']
            print(f"  {nazwa:22s} mediana={delta.median():.2f} SD   max={delta.max():.2f} SD")


def _statystyki_populacyjne():
    import json
    with open("model_config.json", "r", encoding="utf-8") as plik:
        return json.load(plik)["STATS"]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dane", required=True, help="Katalog z plikami Subject_*_raw.csv")
    parser.add_argument("--powtorzenia", type=int, default=12,
                        help="Liczba ziaren RNG na wariant (domyślnie 12)")
    parser.add_argument("--warianty", nargs="+", default=list(WARIANTY), choices=list(WARIANTY))
    parser.add_argument("--wyjscie", default="porownanie_obuoczne_wyniki.csv")
    parser.add_argument("--procesy", type=int, default=None, help="Liczba procesów roboczych")
    args = parser.parse_args()

    pliki = sorted(os.path.join(args.dane, nazwa) for nazwa in os.listdir(args.dane)
                   if nazwa.startswith("Subject_") and nazwa.endswith("_raw.csv"))
    if not pliki:
        print(f"Nie znaleziono plików 'Subject_*_raw.csv' w katalogu {args.dane}.")
        return

    zadania = [(plik, wariant, powtorzenie)
               for plik in pliki
               for wariant in args.warianty
               for powtorzenie in range(args.powtorzenia)]
    print(f"Plików: {len(pliki)}, wariantów: {len(args.warianty)}, "
          f"powtórzeń: {args.powtorzenia} -> {len(zadania)} przebiegów I2MC.")

    wiersze = []
    with futures.ProcessPoolExecutor(max_workers=args.procesy) as executor:
        for numer, wynik in enumerate(executor.map(zadanie, zadania, chunksize=1), 1):
            wiersze.append(wynik)
            if numer % 10 == 0:
                print(f"  {numer}/{len(zadania)}", flush=True)

    wyniki = pd.DataFrame(wiersze)
    wyniki.to_csv(args.wyjscie, index=False)
    raport(wyniki)
    print(f"\nZapisano surowe wyniki w: {args.wyjscie}")


if __name__ == "__main__":
    main()
