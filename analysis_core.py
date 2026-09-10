# Wspólny rdzeń obu analiz: segmentacja I2MC, cechy diagnostyczne i model ryzyka.
# Moduł nie zna geometrii ekranu - dostaje ją (ScreenGeometry) w argumencie, bo
# opisuje ona konkretne nagranie, a nie ten plik.

import pandas as pd
import numpy as np
import I2MC
import contextlib
import traceback
import warnings
import json
import os


# Zapasowa częstotliwość dla analizy grupowej - tylko gdy z pliku nie da się
# wyznaczyć rzeczywistej (patrz estimate_sample_rate_ms).
GROUP_EXPERIMENT_FREQ = 250

# Parametry I2MC. Minimalnego czasu fiksacji nie ustawiamy - zostaje domyślne
# opt['minFixDur'] biblioteki (40 ms).
INTERP_MAX_GAP_MS = 100
WINDOW_SIZE_MS = 200

# I2MC startuje grupowanie 2-means z losowych centroidów (kmeans++), bez ziarna
# ten sam plik daje przy każdym uruchomieniu inny wynik - obserwowany rozstęp
# oceny ryzyka sięgał 0,13. None przywraca zachowanie losowe.
I2MC_RANDOM_SEED = 42

def estimate_sample_rate_ms(time_values, fallback_freq_hz):
    # Okres próbkowania (ms) z rzeczywistych znaczników czasu. Mediana odstępów,
    # bo jest odporna na duplikaty i cofnięcia zegara.
    #
    # Sama kolumna czasu nie idzie dalej w potok - I2MC i tak zakłada równomierne
    # próbkowanie, więc z tego wyliczamy tylko jeden skalar.
    try:
        t = pd.to_numeric(pd.Series(time_values), errors='coerce').to_numpy(dtype=float)
        diffs = np.diff(t)
        diffs = diffs[np.isfinite(diffs) & (diffs > 0)]

        if diffs.size < 10:
            raise ValueError("zbyt mało poprawnych znaczników czasu")

        median_diff = float(np.median(diffs))

        # Jednostki znaczników nie da się odczytać z pliku: Gazepoint podaje
        # sekundy, ETDD70 mikrosekundy, inne eksporty zwykle milisekundy.
        # Wybieramy tę, która daje realistyczną częstotliwość - rozstrzygnięcie
        # jest jednoznaczne, bo zakres 20-2000 Hz to rozpiętość 100x, a jednostki
        # dzieli 1000x. 'ns' bierze się z kolumny przepuszczonej przez datetime64.
        candidate_units = (
            ('s', 1000.0),
            ('ms', 1.0),
            ('us', 0.001),
            ('ns', 0.000001),
        )

        detected = None
        for unit_name, unit_to_ms in candidate_units:
            candidate_diff_ms = median_diff * unit_to_ms
            candidate_freq = 1000.0 / candidate_diff_ms
            if 20.0 <= candidate_freq <= 2000.0:
                detected = (unit_name, candidate_diff_ms, candidate_freq)
                break

        if detected is None:
            raise ValueError(
                f"mediana odstępu między próbkami ({median_diff:.6g}) nie daje "
                f"realistycznej częstotliwości w żadnej ze znanych jednostek "
                f"czasu (s/ms/us/ns)")

        unit_name, median_diff_ms, detected_freq = detected

        print(f"Automatycznie wykryta częstotliwość próbkowania: {detected_freq:.2f} Hz "
              f"(mediana odstępu między próbkami: {median_diff:.6g} {unit_name} = "
              f"{median_diff_ms:.3f} ms)")
        return median_diff_ms

    except Exception as e:
        print(f"Ostrzeżenie: Nie udało się automatycznie wyznaczyć częstotliwości "
              f"próbkowania z kolumny czasu ({e}). Używam wartości domyślnej: "
              f"{fallback_freq_hz} Hz.")
        return 1000.0 / fallback_freq_hz

@contextlib.contextmanager
def _quiet_empty_slice_warnings():
    # Wycisza dwa RuntimeWarning z I2MC.get_fix_stats: dla fiksacji złożonej
    # z samych próbek interpolowanych miary precyzji liczone są z pustej tablicy
    # i wychodzi NaN. Tych kolumn nie używamy w żadnej cesze, a przy analizie
    # grupowej każdy proces roboczy zasypywałby nimi konsolę.
    #
    # Filtr jest wąski celowo - inne ostrzeżenia nadal docierają do użytkownika.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning,
                                message='Mean of empty slice')
        warnings.filterwarnings('ignore', category=RuntimeWarning,
                                message='invalid value encountered in scalar divide')
        yield

def run_i2mc(data, opt):
    # I2MC losuje z globalnego generatora numpy, więc ziarno trzeba ustawić przed
    # wywołaniem, a poprzedni stan odtworzyć - inaczej segmentacja po cichu
    # zmieniałaby losowość w kodzie wywołującym.
    if I2MC_RANDOM_SEED is None:
        with _quiet_empty_slice_warnings():
            return I2MC.I2MC(data, opt, logging=False)

    rng_state = np.random.get_state()
    try:
        np.random.seed(I2MC_RANDOM_SEED)
        with _quiet_empty_slice_warnings():
            return I2MC.I2MC(data, opt, logging=False)
    finally:
        np.random.set_state(rng_state)

def apply_i2mc_segmentation(df, sample_rate_ms, screen):
    # Wrapper na bibliotekę I2MC: przygotowuje dane, składa opcje, zwraca tabelę
    # fiksacji (pusty DataFrame przy niepowodzeniu).
    #
    # Oczekuje kolumn 'x'/'y' (oko lewe lub jedyny sygnał) i opcjonalnie
    # 'x_prawe'/'y_prawe'. Przy dwóch oczach I2MC grupuje każde niezależnie -
    # stąd bierze się deklarowana odporność algorytmu na szum.
    raw_freq = 1000.0 / sample_rate_ms
    freq_nominal = round(raw_freq)
    
    # I2MC wymaga, żeby downsamples były dzielnikami częstotliwości.
    candidate_downsamples = [2, 5, 10]
    valid_downsamples = [d for d in candidate_downsamples if freq_nominal % d == 0]
    
    if not valid_downsamples:
        valid_downsamples = [1]  # nietypowa częstotliwość, np. 60 Hz

    opt = {
        'xres': screen.width_px,
        'yres': screen.height_px,
        'freq': freq_nominal,
        'missingx': np.nan,
        'missingy': np.nan,
        'windowtimeInterp': INTERP_MAX_GAP_MS / 1000.0,
        # Maksymalne przemieszczenie wzroku dopuszczalne w interpolowanej luce -
        # wartość domyślna biblioteki, skalująca się z rozdzielczością. Wcześniejsze
        # 99999 px wyłączało ten test i luka na powrocie do nowego wiersza była
        # zalepiana gładką krzywą mimo przeskoku o ~1400 px.
        'maxdisp': screen.width_px * 0.2 * np.sqrt(2),
        'windowtime': WINDOW_SIZE_MS / 1000.0,
        'steptime': 0.02,
        'downsamples': valid_downsamples,
        'chebyOrder': 8,
        'maxerrors': 100,
        'cutoffstd': 2.0
    }

    # Oś czasu jest syntetyczna i równomierna - I2MC liczy interpolację luk
    # w próbkach, nie w czasie rzeczywistym.
    time_data = df.index.values * sample_rate_ms

    def to_channel(column_name):
        values = df[column_name].values.astype(float)
        return np.where(np.isfinite(values), values, np.nan)

    data = {
        'time': time_data,
        'L_X': to_channel('x'),
        'L_Y': to_channel('y'),
    }

    # Kanał prawego oka podajemy tylko przy realnie niezależnym zapisie. Ten sam
    # sygnał po obu stronach nic nie wnosi, a podwaja czas segmentacji.
    binocular = ('x_prawe' in df.columns and 'y_prawe' in df.columns
                 and df['x_prawe'].notna().any())
    if binocular:
        data['R_X'] = to_channel('x_prawe')
        data['R_Y'] = to_channel('y_prawe')

    mode_label = "obuocznie" if binocular else "jednoocznie"
    print(f"Uruchamianie biblioteki I2MC (freq={freq_nominal}Hz, "
          f"{screen.width_px}x{screen.height_px} px, {mode_label})...")
    
    try:
        res = run_i2mc(data, opt)

        # I2MC zwraca różne struktury zależnie od wersji - szukamy tabeli fiksacji
        # po charakterystycznych kolumnach zamiast zakładać jeden format.

        # Wariant 1: krotka, gdzieś w niej DataFrame albo słownik z fiksacjami.
        if isinstance(res, tuple):
            found_df = None
            for item in res:
                if isinstance(item, pd.DataFrame):
                    cols = item.columns.tolist()
                    if any(c in cols for c in ['xpos', 'Xpos', 'mean_x']) and \
                       any(c in cols for c in ['dur', 'duration', 'dur_ms']):
                        found_df = item
                        break
                elif isinstance(item, dict):
                    if 'final_fixations' in item:
                         found_df = pd.DataFrame(item['final_fixations'])
                         break
                    
                    keys = item.keys()
                    if any(k in keys for k in ['xpos', 'Xpos', 'mean_x']) and \
                       any(k in keys for k in ['dur', 'duration', 'dur_ms']):
                        found_df = pd.DataFrame(item)
                        break
            
            if found_df is not None:
                return found_df
            else:
                print("Błąd I2MC: Zwrócono krotkę, ale nie znaleziono w niej tabeli fiksacji.")
                # Diagnostyka nieznanego formatu.
                print(f"Zawartość krotki (typy): {[type(x) for x in res]}")
                if len(res) > 0 and isinstance(res[0], dict):
                     print(f"Klucze pierwszego elementu (jeśli dict): {list(res[0].keys())}")
                return pd.DataFrame()

        # Wariant 2: słownik bezpośrednio.
        elif isinstance(res, dict):
            if 'final_fixations' in res:
                return pd.DataFrame(res['final_fixations'])
            keys = res.keys()
            if any(k in keys for k in ['xpos', 'Xpos', 'mean_x']):
                return pd.DataFrame(res)
            
        # Wariant 3: brak wyniku.
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
    # Tabela fiksacji z I2MC -> lista zdarzeń FIX/SAC dla calculate_features.
    if fixations_df.empty:
        return []

    events_output = []
    
    # Mapowanie nazw kolumn - różnią się między wersjami I2MC.
    cols = fixations_df.columns
    
    if 'xpos' in cols: x_col = 'xpos'
    elif 'Xpos' in cols: x_col = 'Xpos'
    elif 'mean_x' in cols: x_col = 'mean_x'
    else: 
        print(f"Błąd: Nie znaleziono kolumny pozycji X. Dostępne: {cols}")
        return []

    if 'ypos' in cols: y_col = 'ypos'
    elif 'Ypos' in cols: y_col = 'Ypos'
    elif 'mean_y' in cols: y_col = 'mean_y'
    else: 
        print(f"Błąd: Nie znaleziono kolumny pozycji Y. Dostępne: {cols}")
        return []

    if 'dur' in cols: dur_col = 'dur'
    elif 'duration' in cols: dur_col = 'duration'
    else: 
        print(f"Błąd: Nie znaleziono kolumny czasu trwania. Dostępne: {cols}")
        return []

    start_col = 'startT' if 'startT' in cols else ('start_time' if 'start_time' in cols else None)
    end_col = 'endT' if 'endT' in cols else ('end_time' if 'end_time' in cols else None)

    if start_col:
        fixations_df = fixations_df.sort_values(start_col)  # kolejność chronologiczna
    
    prev_fix = None
    
    # itertuples zamiast iterrows - przy analizie grupowej różnica jest odczuwalna.
    for row in fixations_df.itertuples(index=False):
        x_val = getattr(row, x_col)
        y_val = getattr(row, y_col)
        dur_val = getattr(row, dur_col)
        
        start_val = getattr(row, start_col) if start_col else 0 
        end_val = getattr(row, end_col) if end_col else 0

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
        
        # Sakady nie są mierzone wprost - rekonstruujemy je jako przeskok między
        # kolejnymi fiksacjami.
        if prev_fix is not None:
            sac_event = {
                'type': 'SAC',
                'start_x': prev_fix['end_x'],
                'start_y': prev_fix['end_y'],
                'end_x': curr_fix['start_x'],
                'end_y': curr_fix['start_y'],
                'duration_samples': 0,  # sakada jako przesunięcie natychmiastowe
                'start_time': prev_fix['end_time'],
                'end_time': curr_fix['start_time']
            }
            events_output.append(sac_event)
            
        events_output.append(curr_fix)
        prev_fix = curr_fix
        
    return events_output

def calculate_features(events, sample_rate_ms, screen):
    # Cechy diagnostyczne. Sakadowe wyrażamy w stopniach kąta widzenia, żeby były
    # porównywalne między stanowiskami - stąd 'screen' w argumentach.
    fixations = [e for e in events if e['type'] == 'FIX']
    saccades = [e for e in events if e['type'] == 'SAC']
    
    if not fixations:
        # Brak fiksacji to nieudana segmentacja, a nie prawidłowy pomiar zerowy.
        # Bez tej flagi calculate_risk_score policzyłby z zer fałszywie niskie ryzyko.
        zero_features = {k: 0.0 for k in ['fix_prog_duration', 'fix_reg_duration', 'fix_reg_std',
                                 'fix_dur_std', 'sac_prog_pos_x_mean', 'sac_prog_dist_avg',
                                 'sac_prog_range', 'sac_prog_y_stab', 'sac_reg_y_stab']}
        zero_features['segmentation_failed'] = True
        return zero_features

    prog_fix_durations = []
    reg_fix_durations = []
    all_fix_durations = [f['duration_samples'] * sample_rate_ms for f in fixations]
    
    # Kierunek poprzedzającej sakady dzieli fiksacje na progresywne i regresywne.
    for i in range(1, len(events)):
        curr = events[i]
        prev = events[i-1]
        
        if curr['type'] == 'FIX' and prev['type'] == 'SAC':
            dx = prev['end_x'] - prev['start_x']
            duration = curr['duration_samples'] * sample_rate_ms
            
            if dx > 0:
                prog_fix_durations.append(duration)
            elif dx < 0:
                reg_fix_durations.append(duration)

    sac_prog = [s for s in saccades if (s['end_x'] - s['start_x']) > 0]
    sac_reg = [s for s in saccades if (s['end_x'] - s['start_x']) < 0]

    def get_avg_dist(event_list):
        if not event_list: return 0.0
        dists = [screen.px_to_dva(abs(e['end_x'] - e['start_x'])) for e in event_list]
        return np.mean(dists)

    def get_avg_pos_x(event_list):
        if not event_list: return 0.0
        pos_x = [(e['start_x'] + e['end_x']) / 2.0 for e in event_list]
        return np.mean(pos_x)

    def get_y_stability(event_list):
        if not event_list: return 0.0
        y_diffs = [screen.px_to_dva(abs(e['end_y'] - e['start_y'])) for e in event_list]
        return np.mean(y_diffs)
        
    features = {
        'fix_prog_duration': np.mean(prog_fix_durations) if prog_fix_durations else 0.0,
        'fix_reg_duration': np.mean(reg_fix_durations) if reg_fix_durations else 0.0,
        'fix_reg_std': np.std(reg_fix_durations) if reg_fix_durations else 0.0,
        'fix_dur_std': np.std(all_fix_durations) if all_fix_durations else 0.0,
        'sac_prog_pos_x_mean': get_avg_pos_x(sac_prog),
        'sac_prog_dist_avg': get_avg_dist(sac_prog),
        'sac_prog_range': screen.px_to_dva(np.max([abs(s['end_x'] - s['start_x']) for s in sac_prog])) if sac_prog else 0.0,
        'sac_prog_y_stab': get_y_stability(sac_prog),
        'sac_reg_y_stab': get_y_stability(sac_reg),
        'segmentation_failed': False
    }
    return features

def calculate_risk_score(features):
    # Model logistyczny WRD na pięciu standaryzowanych cechach.
    if features.get('segmentation_failed', False):
        # Jawny błąd zamiast wyniku - cichy false negative byłby tu groźniejszy.
        return {
            'total_score': None,
            'raw_z_score': None,
            'risk_group': "BŁĄD SEGMENTACJI - wynik nieokreślony",
            'threshold': 0.5,
            'details': None,
            'error': "Algorytm I2MC nie wykrył żadnych fiksacji - brak wiarygodnych danych do oceny ryzyka."
        }

    config_path = "model_config.json"
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            model_config = json.load(f)
        STATS = model_config["STATS"]
        intercept = model_config["weights"]["intercept"]
        coefs = model_config["weights"]["coefs"]
    else:
        # Zestaw awaryjny: kopia wag i tabeli STATS z aktualnego modelu (retrening
        # na ETDD70, zadanie T4). Po każdym model_trainer.py trzeba go tu przepisać -
        # rozjazd z plikiem konfiguracyjnym po cichu zmienia wynik.
        print("Ostrzeżenie: Brak pliku 'model_config.json'. Używam wartości "
              "domyślnych wbudowanych w analysis_core.")
        # Czasy fiksacji w ms, cechy sakadowe w DVA - tak jak zwraca je
        # calculate_features.
        STATS = {
            'fix_reg_duration': {'mean': 373.66681717044077, 'std': 93.2618430533182},
            'fix_prog_duration': {'mean': 461.4615754985895, 'std': 131.93910203846818},
            'fix_reg_std': {'mean': 302.76436531336924, 'std': 156.93665461552715},
            'sac_prog_y_stab': {'mean': 0.3007977869400174, 'std': 0.10950221270989573},
            'sac_prog_dist_avg': {'mean': 1.8095335924635316, 'std': 0.4119515398953481}
        }
        intercept = 0.3897398913938465
        coefs = [2.92828952331705, 1.4848261066881088, -1.4040278264859234,
                 0.19615938101889602, 0.3328652125400432]

    val_x1 = features.get('fix_reg_duration', 0.0)
    val_x2 = features.get('fix_prog_duration', 0.0)
    val_x3 = features.get('fix_reg_std', 0.0)
    val_x4 = features.get('sac_prog_y_stab', 0.0)
    val_x5 = features.get('sac_prog_dist_avg', 0.0)

    def get_z_score(val, name):
        m = STATS[name]['mean']
        s = STATS[name]['std']
        if s == 0: return 0.0
        return (val - m) / s

    x1_hat = get_z_score(val_x1, 'fix_reg_duration')
    x2_hat = get_z_score(val_x2, 'fix_prog_duration')
    x3_hat = get_z_score(val_x3, 'fix_reg_std')
    x4_hat = get_z_score(val_x4, 'sac_prog_y_stab')
    x5_hat = get_z_score(val_x5, 'sac_prog_dist_avg')

    # Z = beta_0 + suma(beta_i * x_i), a potem sigmoida -> prawdopodobieństwo.
    logit_Z = intercept + (coefs[0] * x1_hat) + (coefs[1] * x2_hat) + (coefs[2] * x3_hat) + (coefs[3] * x4_hat) + (coefs[4] * x5_hat)

    def sigmoid(z):
        return 1.0 / (1.0 + np.exp(-z))
    
    probability = sigmoid(logit_Z)

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
