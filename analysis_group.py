import pandas as pd
import numpy as np
import os
import glob
import analysis_core as core
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import concurrent.futures

def process_single_subject(filepath, folder_path, generate_plots):
    """Funkcja pomocnicza przetwarzająca pojedynczego uczestnika (dla multiprocessing)"""
    filename = os.path.basename(filepath)
    print(f"Przetwarzanie: {filename}...")
    
    try:
        df = pd.read_csv(filepath)
        
        # Standaryzacja nazw kolumn i przygotowanie danych
        clean_df = pd.DataFrame()
        clean_df['x'] = df['gaze_x_left']
        clean_df['y'] = df['gaze_y_left']

        if 'time' in df.columns:
            sample_rate_ms = core.estimate_sample_rate_ms(df['time'], core.GROUP_EXPERIMENT_FREQ)
        else:
            print(f"  -> Brak kolumny 'time' w {filename}, używam domyślnej "
                  f"częstotliwości {core.GROUP_EXPERIMENT_FREQ} Hz.")
            sample_rate_ms = 1000.0 / core.GROUP_EXPERIMENT_FREQ

        # Brakujące/nieprawidłowe próbki oznaczamy jako NaN zamiast usuwać wiersze:
        # usunięcie wiersza przesuwa oś czasu, więc I2MC nigdy nie zobaczyłby luki
        # do interpolacji (patrz core.INTERP_MAX_GAP_MS).
        invalid_mask = ~((clean_df['x'] > 1) & (clean_df['y'] > 1))
        clean_df.loc[invalid_mask, ['x', 'y']] = np.nan

        if clean_df['x'].notna().sum() == 0:
            print(f"  -> Pominięto {filename} (brak poprawnych danych)")
            return None

        # --- POTOK ANALIZY I2MC ---
        df_segmented = core.apply_i2mc_segmentation(clean_df, sample_rate_ms)
        
        events = core.classify_movements(df_segmented, sample_rate_ms)
        features = core.calculate_features(events, sample_rate_ms)
        diagnosis = core.calculate_risk_score(features)

        if diagnosis['total_score'] is None:
            print(f"  -> Ostrzeżenie {filename}: {diagnosis.get('error', 'segmentacja nieudana')}")

        # --- WIZUALIZACJA (OPCJONALNA) ---
        if generate_plots:
            try:
                viz_out_path = os.path.splitext(filepath)[0] + "_scanpath.png"
                
                plt.figure(figsize=(16, 9))
                
                bg_filename = "bodziec.jpg"
                bg_path = os.path.join(folder_path, bg_filename)
                
                if os.path.exists(bg_path):
                    img = mpimg.imread(bg_path)
                    plt.imshow(img, extent=[0, core.SCREEN_WIDTH, core.SCREEN_HEIGHT, 0])
                else:
                    plt.xlim(0, core.SCREEN_WIDTH)
                    plt.ylim(core.SCREEN_HEIGHT, 0)
                    plt.text(core.SCREEN_WIDTH/2, core.SCREEN_HEIGHT/2, 
                             f"Brak pliku tła: {bg_filename}", ha='center', va='center')
                
                fixations = [e for e in events if e['type'] == 'FIX']
                
                if len(fixations) > 1:
                    fx = [f['mean_x'] for f in fixations]
                    fy = [f['mean_y'] for f in fixations]
                    plt.plot(fx, fy, c='blue', alpha=0.5, linewidth=1, zorder=1)
                    
                for f in fixations:
                    sz = max(20, f.get('duration_samples', 10) * 2) 
                    color = 'lime'
                    if f == fixations[0]: color = 'yellow'
                    if f == fixations[-1]: color = 'red'
                    plt.scatter(f['mean_x'], f['mean_y'], s=sz, c=color, 
                                edgecolors='black', alpha=0.9, zorder=2)
                    
                plt.axis('off')
                plt.title(f"Ścieżka wzroku podczas Zadania 1: Czytanie tekstu - {filename}")
                plt.tight_layout()
                plt.savefig(viz_out_path)
                plt.close('all') # Zamknięcie figury uwalnia pamięć RAM
                
            except Exception as viz_e:
                print(f"  -> Błąd generowania wykresu dla {filename}: {viz_e}")
                plt.close('all')

        # Zbieranie wyników
        result_row = {
            'filename': filename,
            'score': diagnosis['total_score'],
            'risk_group': diagnosis['risk_group'],
            **features 
        }
        return result_row
        
    except Exception as e:
        print(f"  -> Błąd pliku {filename}: {e}")
        return None

def run_analysis(folder_path, generate_plots=True):
    print(f"Rozpoczynanie analizy grupowej (I2MC) w folderze: {folder_path}")
    
    files = glob.glob(os.path.join(folder_path, "Subject_*_raw.csv"))
    
    if not files:
        return "Nie znaleziono plików pasujących do wzorca 'Subject_*_raw.csv' w wybranym folderze."
    
    results_list = []
    
    # Wielowątkowość za pomocą ProcessPoolExecutor
    print(f"Uruchamianie przetwarzania wielowątkowego dla {len(files)} plików...")
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Przekazywanie argumentów do funkcji process_single_subject
        futures = {executor.submit(process_single_subject, fp, folder_path, generate_plots): fp for fp in files}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res is not None:
                results_list.append(res)
            
    if not results_list:
        return "Brak poprawnie przetworzonych plików."
        
    # Zapis wyników zbiorczych
    summary_df = pd.DataFrame(results_list)
    output_path = os.path.join(folder_path, "#wyniki_grupowe.csv")
    summary_df.to_csv(output_path, index=False)
    
    return (
        f"Zakończono analizę grupową I2MC.\n"
        f"Przetworzono plików: {len(results_list)}\n"
        f"Zapisano raport w: {output_path}"
    )