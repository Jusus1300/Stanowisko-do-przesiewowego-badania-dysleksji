import pandas as pd
import numpy as np
import I2MC
import traceback
import json
import os

# Stałe ekranu
SCREEN_WIDTH = 1680
SCREEN_HEIGHT = 1050
SCREEN_WIDTH_CM = 47.4  # Parametry fizyczne ekranu (estymowane)   
VIEWING_DISTANCE_CM = 60.0

# Częstotliwość próbkowania eyetrackera w grupowym eksperymencie
GROUP_EXPERIMENT_FREQ = 250

# === PARAMETRY ALGORYTMU I2MC ===
INTERP_MAX_GAP_MS = 100
WINDOW_SIZE_MS = 200 
MIN_FIX_DURATION_MS = 40

def px_to_dva(px_distance):
    # Konwertuje dystans w pikselach na stopnie kąta widzenia (DVA).
    cm_per_px = SCREEN_WIDTH_CM / SCREEN_WIDTH
    dist_cm = px_distance * cm_per_px
    return 2 * np.degrees(np.arctan(dist_cm / (2 * VIEWING_DISTANCE_CM)))

def apply_i2mc_segmentation(df, sample_rate_ms):

    # Wrapper dla biblioteki I2MC.
    # Przygotowuje dane, konfiguruje opcje i uruchamia algorytm.
    # Zwraca DataFrame z wykrytymi fiksacjami.

    # 1. Obliczanie częstotliwości
    raw_freq = 1000.0 / sample_rate_ms
    # I2MC wymaga, aby downsamples były idealnymi dzielnikami częstotliwości.
    freq_nominal = round(raw_freq)
    
    # 2. Dynamiczne dobieranie downsamples
    candidate_downsamples = [2, 5, 10]
    valid_downsamples = [d for d in candidate_downsamples if freq_nominal % d == 0]
    
    # Zabezpieczenie na wypadek nietypowej częstotliwości (np. 60Hz)
    if not valid_downsamples:
        valid_downsamples = [1]

    # 3. Konfiguracja opcji
    opt = {
        'xres': SCREEN_WIDTH,
        'yres': SCREEN_HEIGHT,
        'freq': freq_nominal,
        'missingx': np.nan,
        'missingy': np.nan,
        'windowtimeInterp': INTERP_MAX_GAP_MS / 1000.0,
        'maxdisp': 99999, 
        'windowtime': WINDOW_SIZE_MS / 1000.0,
        'steptime': 0.02,
        'downsamples': valid_downsamples,
        'chebyOrder': 8,
        'maxerrors': 100,
        'cutoffstd': 2.0
    }

    # 4. Przygotowanie danych wejściowych
    x_data = df['x'].values
    y_data = df['y'].values
    
    x_data = np.where(np.isfinite(x_data), x_data, np.nan)
    y_data = np.where(np.isfinite(y_data), y_data, np.nan)
    
    time_data = df.index.values * sample_rate_ms
    
    data = {
        'time': time_data,
        'L_X': x_data,
        'L_Y': y_data,
        'R_X': x_data,
        'R_Y': y_data, 
    }

    print(f"Uruchamianie biblioteki I2MC (freq={freq_nominal}Hz)...")
    
    try:
        # Uruchomienie I2MC
        # logging=False wycisza printy biblioteki
        res = I2MC.I2MC(data, opt, logging=False)
        
        # === OBSŁUGA RÓŻNYCH TYPÓW ZWRACANYCH DANYCH ===
        
        # Przypadek 1: Tuple (krotka) - [dict, DataFrame, dict]
        if isinstance(res, tuple):
            found_df = None
            for item in res:
                if isinstance(item, pd.DataFrame):
                    # Weryfikacja czy to tabela fiksacji
                    cols = item.columns.tolist()
                    # Szukamy kluczowych kolumn
                    if any(c in cols for c in ['xpos', 'Xpos', 'mean_x']) and \
                       any(c in cols for c in ['dur', 'duration', 'dur_ms']):
                        found_df = item
                        break
                elif isinstance(item, dict):
                    # Podprzypadek A: Słownik zagnieżdżony w kluczu 'final_fixations'
                    if 'final_fixations' in item:
                         found_df = pd.DataFrame(item['final_fixations'])
                         break
                    
                    # Podprzypadek B: Słownik JEST danymi fiksacji (bez klucza wrappującego)
                    # Sprawdzamy czy posiada klucze danych
                    keys = item.keys()
                    if any(k in keys for k in ['xpos', 'Xpos', 'mean_x']) and \
                       any(k in keys for k in ['dur', 'duration', 'dur_ms']):
                        found_df = pd.DataFrame(item)
                        break
            
            if found_df is not None:
                return found_df
            else:
                print("Błąd I2MC: Zwrócono krotkę, ale nie znaleziono w niej tabeli fiksacji.")
                # Debug: wypisz typy elementów w krotce
                print(f"Zawartość krotki (typy): {[type(x) for x in res]}")
                if len(res) > 0 and isinstance(res[0], dict):
                     print(f"Klucze pierwszego elementu (jeśli dict): {list(res[0].keys())}")
                return pd.DataFrame()

        # Przypadek 2: Słownik (bezpośrednio)
        elif isinstance(res, dict):
            if 'final_fixations' in res:
                return pd.DataFrame(res['final_fixations'])
            # Sprawdzenie czy słownik to dane bezpośrednie
            keys = res.keys()
            if any(k in keys for k in ['xpos', 'Xpos', 'mean_x']):
                return pd.DataFrame(res)
            
        # Przypadek 3: Błędy lub brak danych
        elif res is False or res is None:
             print("I2MC: Brak fiksacji (zbyt mało danych lub szum).")
             return pd.DataFrame()
        else:
            print(f"I2MC: Nieznany format wyniku: {type(res)}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Błąd krytyczny w wrapperze I2MC: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def classify_movements(fixations_df, sample_rate_ms):

    # Konwertuje wynik biblioteki I2MC (tabela fiksacji) na listę zdarzeń (FIX/SAC)
    # kompatybilną z funkcją calculate_features.

    if fixations_df.empty:
        return []

    events_output = []
    
    # === MAPOWANIE NAZW KOLUMN ===
    # I2MC może zwracać różne nazwy w zależności od wersji.
    # Mapujemy je na wewnętrzne zmienne.
    cols = fixations_df.columns
    
    # 1. Pozycja X
    if 'xpos' in cols: x_col = 'xpos'
    elif 'Xpos' in cols: x_col = 'Xpos'
    elif 'mean_x' in cols: x_col = 'mean_x'
    else: 
        print(f"Błąd: Nie znaleziono kolumny pozycji X. Dostępne: {cols}")
        return []

    # 2. Pozycja Y
    if 'ypos' in cols: y_col = 'ypos'
    elif 'Ypos' in cols: y_col = 'Ypos'
    elif 'mean_y' in cols: y_col = 'mean_y'
    else: 
        print(f"Błąd: Nie znaleziono kolumny pozycji Y. Dostępne: {cols}")
        return []

    # 3. Czas trwania
    if 'dur' in cols: dur_col = 'dur'
    elif 'duration' in cols: dur_col = 'duration'
    else: 
        print(f"Błąd: Nie znaleziono kolumny czasu trwania. Dostępne: {cols}")
        return []

    # 4. Czas startu (opcjonalny do sortowania)
    start_col = 'startT' if 'startT' in cols else ('start_time' if 'start_time' in cols else None)
    end_col = 'endT' if 'endT' in cols else ('end_time' if 'end_time' in cols else None)

   # Sortowanie chronologiczne
    if start_col:
        fixations_df = fixations_df.sort_values(start_col)
    
    prev_fix = None
    
    # Zoptymalizowana iteracja za pomocą itertuples
    for row in fixations_df.itertuples(index=False):
        # Pobranie danych za pomocą getattr (szybsze niż iterrows)
        x_val = getattr(row, x_col)
        y_val = getattr(row, y_col)
        dur_val = getattr(row, dur_col)
        
        # Jeśli brakuje kolumn czasu start/stop, estymuje je na podstawie duracji
        start_val = getattr(row, start_col) if start_col else 0 
        end_val = getattr(row, end_col) if end_col else 0

        # Konwersja czasu trwania (ms) na liczbę próbek
        dur_samples = dur_val / sample_rate_ms if sample_rate_ms > 0 else 0
        
        curr_fix = {
            'type': 'FIX',
            'duration_samples': dur_samples, 
            'mean_x': x_val,
            'mean_y': y_val,
            'start_x': x_val, 
            'start_y': y_val,
            'end_x': x_val,
            'end_y': y_val,
            'start_time': start_val,
            'end_time': end_val
        }
        
        # Rekonstrukcja sakady (ruch między fiksacjami)
        if prev_fix is not None:
            sac_event = {
                'type': 'SAC',
                'start_x': prev_fix['end_x'],
                'start_y': prev_fix['end_y'],
                'end_x': curr_fix['start_x'],
                'end_y': curr_fix['start_y'],
                'duration_samples': 0, # Modeluje sakadę jako natychmiastowe przesunięcie
                'start_time': prev_fix['end_time'],
                'end_time': curr_fix['start_time']
            }
            events_output.append(sac_event)
            
        events_output.append(curr_fix)
        prev_fix = curr_fix
        
    return events_output

def calculate_features(events, sample_rate_ms):
    # Obliczanie cech diagnostycznych na podstawie listy zdarzeń.
    fixations = [e for e in events if e['type'] == 'FIX']
    saccades = [e for e in events if e['type'] == 'SAC']
    
    if not fixations:
        return {k: 0.0 for k in ['fix_prog_duration', 'fix_reg_duration', 'fix_reg_std', 
                                 'fix_dur_std', 'sac_prog_pos_x_mean', 'sac_prog_dist_avg', 
                                 'sac_prog_range', 'sac_prog_y_stab', 'sac_reg_y_stab']}

    prog_fix_durations = []
    reg_fix_durations = []
    all_fix_durations = [f['duration_samples'] * sample_rate_ms for f in fixations]
    
    # Analiza sekwencji (progresje vs regresje)
    for i in range(1, len(events)):
        curr = events[i]
        prev = events[i-1]
        
        if curr['type'] == 'FIX' and prev['type'] == 'SAC':
            dx = prev['end_x'] - prev['start_x'] # Kierunek sakady
            duration = curr['duration_samples'] * sample_rate_ms
            
            if dx > 0:  # Próg pikselowy dla ruchu w prawo
                prog_fix_durations.append(duration)
            elif dx < 0: # Próg pikselowy dla ruchu w lewo (regresja)
                reg_fix_durations.append(duration)

    sac_prog = [s for s in saccades if (s['end_x'] - s['start_x']) > 0]
    sac_reg = [s for s in saccades if (s['end_x'] - s['start_x']) < 0]

    def get_avg_dist(event_list):
        if not event_list: return 0.0
        dists = [px_to_dva(abs(e['end_x'] - e['start_x'])) for e in event_list]
        return np.mean(dists)

    def get_avg_pos_x(event_list):
        if not event_list: return 0.0
        pos_x = [(e['start_x'] + e['end_x']) / 2.0 for e in event_list]
        return np.mean(pos_x)

    def get_y_stability(event_list):
        if not event_list: return 0.0
        y_diffs = [px_to_dva(abs(e['end_y'] - e['start_y'])) for e in event_list]
        return np.mean(y_diffs)
        
    features = {
        'fix_prog_duration': np.mean(prog_fix_durations) if prog_fix_durations else 0.0,
        'fix_reg_duration': np.mean(reg_fix_durations) if reg_fix_durations else 0.0,
        'fix_reg_std': np.std(reg_fix_durations) if reg_fix_durations else 0.0,
        'fix_dur_std': np.std(all_fix_durations) if all_fix_durations else 0.0,
        'sac_prog_pos_x_mean': get_avg_pos_x(sac_prog),
        'sac_prog_dist_avg': get_avg_dist(sac_prog),
        'sac_prog_range': px_to_dva(np.max([abs(s['end_x'] - s['start_x']) for s in sac_prog])) if sac_prog else 0.0,
        'sac_prog_y_stab': get_y_stability(sac_prog),
        'sac_reg_y_stab': get_y_stability(sac_reg)
    }
    return features

def calculate_risk_score(features):

    # Algorytm oceny ryzyka dysleksji (Model Logistyczny WRD).
    # Opiera się na 5 kluczowych parametrach ruchu oczu.
  
    config_path = "model_config.json"
    
    # Próba wczytania dynamicznych wartości STATS i wag z pliku tekstowego
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            model_config = json.load(f)
        STATS = model_config["STATS"]
        intercept = model_config["weights"]["intercept"]
        coefs = model_config["weights"]["coefs"]
    else:
        print("Ostrzeżenie: Brak pliku 'model_config.json'. Używam starych, domyślnych wartości.")
        # Statystyki populacyjne do standaryzacji (wartości domyślne)
        STATS = {
            'fix_reg_duration': {'mean': 343.8833, 'std': 77.5709},
            'fix_prog_duration': {'mean': 431.1039, 'std': 109.1987},
            'fix_reg_std': {'mean': 272.4751, 'std': 128.4067},
            'sac_prog_y_stab': {'mean': 14.2653, 'std': 5.1284},
            'sac_prog_dist_avg': {'mean': 65.2241, 'std': 15.8542}
        }
        intercept = 0.3258677392698436
        coefs = [2.5853168, 0.71192308, -0.61731528, 1.00967702, -0.17200714]

    # Pobranie cech z obliczonych danych
    val_x1 = features.get('fix_reg_duration', 0.0)
    val_x2 = features.get('fix_prog_duration', 0.0)
    val_x3 = features.get('fix_reg_std', 0.0)
    val_x4 = features.get('sac_prog_y_stab', 0.0)
    val_x5 = features.get('sac_prog_dist_avg', 0.0)

    # Funkcja pomocnicza do standaryzacji
    def get_z_score(val, name):
        m = STATS[name]['mean']
        s = STATS[name]['std']
        if s == 0: return 0.0
        return (val - m) / s

    # Obliczenie wartości standaryzowanych (x_hat)
    x1_hat = get_z_score(val_x1, 'fix_reg_duration')
    x2_hat = get_z_score(val_x2, 'fix_prog_duration')
    x3_hat = get_z_score(val_x3, 'fix_reg_std')
    x4_hat = get_z_score(val_x4, 'sac_prog_y_stab')
    x5_hat = get_z_score(val_x5, 'sac_prog_dist_avg')

    # Obliczenie Logitu (Z) z wykorzystaniem wczytanych wag z pliku
    # Wzór: Z = beta_0 + beta_1*x1 + beta_2*x2 + ...
    logit_Z = intercept + (coefs[0] * x1_hat) + (coefs[1] * x2_hat) + (coefs[2] * x3_hat) + (coefs[3] * x4_hat) + (coefs[4] * x5_hat)

    # Funkcja sigmoidalna: P = 1 / (1 + e^-Z)
    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-z))
    
    probability = sigmoid(logit_Z)

    # Interpretacja wyniku
    if probability > 0.5:
        risk_group = "Wysokie ryzyko"
    else:
        risk_group = "Niskie ryzyko"

    return {
        'total_score': round(probability, 2),
        'raw_z_score': round(logit_Z, 3),
        'risk_group': risk_group,
        'threshold': 0.5,
        'details': {
            'x1_fix_reg_dur_z': round(x1_hat, 2),
            'x2_fix_prog_dur_z': round(x2_hat, 2),
            'x3_fix_reg_std_z': round(x3_hat, 2),
            'x4_sac_y_stab_z': round(x4_hat, 2),
            'x5_sac_dist_z': round(x5_hat, 2)
        }
    }