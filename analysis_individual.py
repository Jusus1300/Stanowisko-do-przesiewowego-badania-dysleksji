import pandas as pd
import numpy as np
import analysis_core as core
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
from experiment_config import EYETRACKER_FREQ

def run_analysis(file_path):
    print(f"Rozpoczynanie analizy indywidualnej (Algorytm I2MC) dla: {file_path}")
    
    try:
        # Wczytanie danych
        df = pd.read_csv(file_path)
        
        # 1. Przygotowanie sygnału
        clean_df = pd.DataFrame()
        clean_df['x'] = df['BPOGX'] * core.SCREEN_WIDTH
        clean_df['y'] = df['BPOGY'] * core.SCREEN_HEIGHT

        if 'TIME' in df.columns:
            sample_rate_ms = core.estimate_sample_rate_ms(df['TIME'], EYETRACKER_FREQ)
        else:
            print(f"Brak kolumny 'TIME' w pliku, używam domyślnej częstotliwości "
                  f"{EYETRACKER_FREQ} Hz.")
            sample_rate_ms = 1000.0 / EYETRACKER_FREQ

        # Brakujące/nieprawidłowe próbki (poza zakresem ekranu) oznaczamy jako NaN
        # zamiast usuwać wiersze: usunięcie wiersza przesuwa oś czasu, więc I2MC
        # nigdy nie zobaczyłby luki do interpolacji (patrz core.INTERP_MAX_GAP_MS).
        valid_mask = (
            (df['BPOGX'] >= 0) & (df['BPOGX'] <= 1) &
            (df['BPOGY'] >= 0) & (df['BPOGY'] <= 1)
        )
        clean_df.loc[~valid_mask, ['x', 'y']] = np.nan

        if clean_df['x'].notna().sum() == 0:
            return "Błąd: Brak poprawnych danych w pliku."

        # 2. Segmentacja - Wywołanie I2MC
        df_segmented = core.apply_i2mc_segmentation(clean_df, sample_rate_ms)
        
        # 3. Klasyfikacja ruchów i scalanie
        events = core.classify_movements(df_segmented, sample_rate_ms)
        
        # Generowanie wizualizacji
        viz_status = "Nie wygenerowano wykresu."
        try:
            input_dir = os.path.dirname(file_path)
            img_filename = "zrzut_ekranu_bodzca.png"
            img_path = os.path.join(input_dir, img_filename)
            foldername = os.path.basename(os.path.dirname(file_path))
            output_plot_path = os.path.join(input_dir, f"#scanpath_{foldername}.png")
            report_path = os.path.join(input_dir, f"#raport_{foldername}.txt")

            plt.figure(figsize=(16, 9))
            
            # Wczytanie tła
            if os.path.exists(img_path):
                img = mpimg.imread(img_path)
                plt.imshow(img, extent=[0, core.SCREEN_WIDTH, core.SCREEN_HEIGHT, 0])
            else:
                plt.xlim(0, core.SCREEN_WIDTH)
                plt.ylim(core.SCREEN_HEIGHT, 0)
                plt.text(core.SCREEN_WIDTH/2, core.SCREEN_HEIGHT/2, 
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
        features = core.calculate_features(events, sample_rate_ms)
        
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
            f"Status wizualizacji: {viz_status}\n"
            f"------------------------------------\n"
            f"CECHY DIAGNOSTYCZNE:\n"
            f"1. Śr. czas fiksacji PROG: {features['fix_prog_duration']:.2f} ms\n"
            f"2. Śr. czas fiksacji REGR: {features['fix_reg_duration']:.2f} ms\n"
            f"3. Odchylenie std REGR:    {features['fix_reg_std']:.2f} ms\n"
            f"4. Śr. dystans sakad PROG: {features['sac_prog_dist_avg']:.2f} px\n"
            f"5. Max zakres sakad PROG:  {features['sac_prog_range']:.2f} px\n"
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
