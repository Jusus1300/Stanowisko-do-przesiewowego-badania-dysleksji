import pandas as pd
import numpy as np
import analysis_core as core
import screen_geometry
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
from experiment_config import EYETRACKER_FREQ

def run_analysis(file_path):
    print(f"Rozpoczynanie analizy indywidualnej (Algorytm I2MC) dla: {file_path}")
    
    try:
        # Wczytanie danych
        df = pd.read_csv(file_path)
        input_dir = os.path.dirname(file_path)

        # 0. Geometria stanowiska, na którym powstało nagranie.
        #
        # GP3 podaje współrzędne znormalizowane do rozmiaru ekranu (0-1), więc
        # to geometria decyduje, na jaką liczbę pikseli, a dalej na ile stopni
        # kąta widzenia, przelicza się każdy ruch oka. Wcześniej potok mnożył
        # je przez stałe ekranu zbioru ETDD70 (1680x1050, 47,4 cm), czyli
        # przez parametry zupełnie innego stanowiska - wynik był systematycznie
        # przeskalowany, a I2MC dostawał xres/yres niezgodne z danymi.
        # Parametry bierzemy więc z pliku zapisanego przy nagraniu, a gdy go
        # brak - z experiment_config.py (patrz screen_geometry.for_recording).
        screen = screen_geometry.for_recording(input_dir)
        print(f"Geometria ekranu nagrania: {screen.describe()}")

        # 1. Przygotowanie sygnału
        #
        # Nagrania z GP3 zawierają punkt spojrzenia osobno dla każdego oka
        # (LPOG*/RPOG*) oraz uśredniony przez okulograf punkt BPOG. Do
        # segmentacji podajemy oba oczy, żeby I2MC mógł grupować je
        # niezależnie. Starsze nagrania, sprzed włączenia ENABLE_SEND_POG_LEFT
        # i ENABLE_SEND_POG_RIGHT w gazepoint.py, mają tylko BPOG - wtedy
        # potok schodzi do trybu jednoocznego na tym uśrednionym punkcie.
        has_both_eyes = {'LPOGX', 'LPOGY', 'RPOGX', 'RPOGY'} <= set(df.columns)

        clean_df = pd.DataFrame()
        if has_both_eyes:
            clean_df['x'] = df['LPOGX'] * screen.width_px
            clean_df['y'] = df['LPOGY'] * screen.height_px
            clean_df['x_prawe'] = df['RPOGX'] * screen.width_px
            clean_df['y_prawe'] = df['RPOGY'] * screen.height_px
        else:
            print("Brak kolumn LPOG*/RPOG* - nagranie sprzed przejścia na zapis "
                  "obuoczny. Analiza jednooczna na uśrednionym punkcie BPOG.")
            clean_df['x'] = df['BPOGX'] * screen.width_px
            clean_df['y'] = df['BPOGY'] * screen.height_px

        if 'TIME' in df.columns:
            sample_rate_ms = core.estimate_sample_rate_ms(df['TIME'], EYETRACKER_FREQ)
        else:
            print(f"Brak kolumny 'TIME' w pliku, używam domyślnej częstotliwości "
                  f"{EYETRACKER_FREQ} Hz.")
            sample_rate_ms = 1000.0 / EYETRACKER_FREQ

        # Brakujące/nieprawidłowe próbki (poza zakresem ekranu) oznaczamy jako NaN
        # zamiast usuwać wiersze: usunięcie wiersza przesuwa oś czasu, więc I2MC
        # nigdy nie zobaczyłby luki do interpolacji (patrz core.INTERP_MAX_GAP_MS).
        #
        # Filtr działa osobno na każdym oku - próbka odrzucona na jednym oku nie
        # unieważnia drugiego, bo I2MC potrafi skorzystać z oka pozostałego
        # (I2MC.average_eyes). Poza zakresem ekranu sprawdzana jest też flaga
        # poprawności z okulografu (POGV): GP3 przy zgubionym oku podaje ostatnią
        # znaną pozycję z POGV=0, a taka próbka mieści się w zakresie 0-1
        # i przeszłaby przez sam test zakresu.
        def valid_mask(x_col, y_col, v_col):
            mask = (
                (df[x_col] >= 0) & (df[x_col] <= 1) &
                (df[y_col] >= 0) & (df[y_col] <= 1)
            )
            if v_col in df.columns:
                mask &= pd.to_numeric(df[v_col], errors='coerce') == 1
            return mask

        if has_both_eyes:
            clean_df.loc[~valid_mask('LPOGX', 'LPOGY', 'LPOGV'), ['x', 'y']] = np.nan
            clean_df.loc[~valid_mask('RPOGX', 'RPOGY', 'RPOGV'),
                         ['x_prawe', 'y_prawe']] = np.nan
        else:
            clean_df.loc[~valid_mask('BPOGX', 'BPOGY', 'BPOGV'), ['x', 'y']] = np.nan

        # Oko bez ani jednej poprawnej próbki wypada z analizy zamiast trafiać
        # do I2MC jako kolumna samych NaN - grupowanie takiego kanału kończy się
        # błędem i przewraca segmentację także dla oka sprawnego.
        left_ok = clean_df['x'].notna().any()
        right_ok = has_both_eyes and clean_df['x_prawe'].notna().any()

        if not left_ok and not right_ok:
            return "Błąd: Brak poprawnych danych w pliku."

        if left_ok and right_ok:
            tryb_segmentacji = "obuoczny (LPOG + RPOG)"
        elif left_ok:
            clean_df = clean_df[['x', 'y']]
            if has_both_eyes:
                print("Prawe oko bez poprawnych próbek - analiza jednooczna (lewe).")
                tryb_segmentacji = "jednooczny - lewe oko (prawe bez poprawnych próbek)"
            else:
                tryb_segmentacji = "jednooczny - uśredniony punkt BPOG"
        else:
            clean_df = clean_df[['x_prawe', 'y_prawe']].rename(
                columns={'x_prawe': 'x', 'y_prawe': 'y'})
            print("Lewe oko bez poprawnych próbek - analiza jednooczna (prawe).")
            tryb_segmentacji = "jednooczny - prawe oko (lewe bez poprawnych próbek)"

        # 2. Segmentacja - Wywołanie I2MC
        df_segmented = core.apply_i2mc_segmentation(clean_df, sample_rate_ms, screen)
        
        # 3. Klasyfikacja ruchów i scalanie
        events = core.classify_movements(df_segmented, sample_rate_ms)
        
        # Generowanie wizualizacji
        viz_status = "Nie wygenerowano wykresu."
        try:
            img_filename = screen_geometry.STIMULUS_SCREENSHOT
            img_path = os.path.join(input_dir, img_filename)
            foldername = os.path.basename(os.path.dirname(file_path))
            output_plot_path = os.path.join(input_dir, f"#scanpath_{foldername}.png")
            report_path = os.path.join(input_dir, f"#raport_{foldername}.txt")

            plt.figure(figsize=(16, 9))
            
            # Wczytanie tła
            if os.path.exists(img_path):
                img = mpimg.imread(img_path)
                plt.imshow(img, extent=[0, screen.width_px, screen.height_px, 0])
            else:
                plt.xlim(0, screen.width_px)
                plt.ylim(screen.height_px, 0)
                plt.text(screen.width_px/2, screen.height_px/2, 
                         "Brak pliku tła", ha='center', va='center')

            # Rysowanie fiksacji i ścieżki
            fixations = [e for e in events if e['type'] == 'FIX']
            
            # 1. Rysowanie linii łączących (ścieżka wzroku)
            if len(fixations) > 1:
                x_coords = [f['mean_x'] for f in fixations]
                y_coords = [f['mean_y'] for f in fixations]
                plt.plot(x_coords, y_coords, c='blue', alpha=0.4, linewidth=1, zorder=1)

            # 2. Rysowanie fiksacji (kółka)
            for f in fixations:
                size = max(20, f['duration_samples'] * 2)
                color = 'lime'
                if f == fixations[0]: color = 'yellow'
                if f == fixations[-1]: color = 'red'
                
                plt.scatter(f['mean_x'], f['mean_y'], s=size, c=color, 
                            alpha=0.9, edgecolors='black', zorder=2)

            plt.title(f"Ścieżka wzroku podczas Zadania 1: Czytanie tekstu - {foldername}")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_plot_path, dpi=100)
            plt.close()
            viz_status = f"Wygenerowano wykres: {os.path.basename(output_plot_path)}"
            
        except Exception as viz_e:
            viz_status = f"Błąd wizualizacji: {str(viz_e)}"

        # 4. Cechy
        features = core.calculate_features(events, sample_rate_ms, screen)
        
        # 5. Model
        diagnosis = core.calculate_risk_score(features)

        # 6. Raport
        behav_path = os.path.join(input_dir, "wyniki_behawioralne.csv")
        behav_info = "\n------------------------------------\nWYNIKI BEHAWIORALNE:\n"
        if os.path.exists(behav_path):
            try:
                behav_df = pd.read_csv(behav_path)
                for index, row in behav_df.iterrows():
                    popr = row.get('CzyPoprawna', 'N/A')
                    if popr == True:
                        popr = "TAK"
                    elif popr == False:
                        popr = "NIE"
                    czas = row.get('CzasReakcji_s', 'N/A')
                    behav_info += f"Czy odpowiedź jest poprawna?: {popr}, Czas reakcji: {czas} s\n"
            except Exception as e:
                behav_info += f"Błąd podczas odczytu pliku z wynikami behawioralnymi: {str(e)}\n"
        else:
            behav_info += "Brak pliku wyniki_behawioralne.csv w docelowym folderze.\n"

        report = (
            f"\n=== WYNIKI ANALIZY INDYWIDUALNEJ===\n"
            f"Plik: {file_path}\n"
            f"Wykrytych fiksacji: {len([e for e in events if e['type'] == 'FIX'])}\n"
            f"Częstotliwość próbkowania: {sample_rate_ms:.2f} ms\n"
            f"Geometria ekranu: {screen.describe()}\n"
            f"Tryb segmentacji: {tryb_segmentacji}\n"
            f"Status wizualizacji: {viz_status}\n"
            f"------------------------------------\n"
            f"CECHY DIAGNOSTYCZNE:\n"
            f"1. Śr. czas fiksacji PROG: {features['fix_prog_duration']:.2f} ms\n"
            f"2. Śr. czas fiksacji REGR: {features['fix_reg_duration']:.2f} ms\n"
            f"3. Odchylenie std REGR:    {features['fix_reg_std']:.2f} ms\n"
            f"4. Śr. dystans sakad PROG: {features['sac_prog_dist_avg']:.2f} deg\n"
            f"5. Max zakres sakad PROG:  {features['sac_prog_range']:.2f} deg\n"
            f"6. Stab. Y (Sakady PROG):  {features['sac_prog_y_stab']:.2f} deg\n"
            f"7. Stab. Y (Sakady REGR):  {features['sac_reg_y_stab']:.2f} deg\n"
            f"{behav_info}"
            f"------------------------------------\n"
        )

        if diagnosis['total_score'] is None:
            report += (
                f"WYNIK MODELU: BRAK - {diagnosis.get('error', 'segmentacja nieudana')}\n"
                f"KLASYFIKACJA: {diagnosis['risk_group']}\n"
            )
        else:
            report += (
                f"WYNIK MODELU: {diagnosis['total_score']:.3f} (Próg: {diagnosis['threshold']})\n"
                f"KLASYFIKACJA: {diagnosis['risk_group']}\n"
            )

        # Zapis raportu do pliku tekstowego obok wykresu
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(report)

        return report

    except Exception as e:
        return f"Wystąpił błąd podczas analizy: {str(e)}"
