# Konfiguracja stanowiska badawczego - stałe eksperymentu i geometria ekranu,
# na którym powstaje nagranie. Importowana i przez eksperyment, i przez analizę,
# więc poza stdlib nie ma zależności (screeninfo i PIL wczytywane są leniwie).

import json
import math
import os
from dataclasses import dataclass, asdict

# --- Ścieżki ---
DATA_FOLDER = "dane_z_badan"

BACKGROUND_IMG = "dane_do_eksperymentu/grafiki/tlo_kokpit.jpg"
TARGET_IMG = "dane_do_eksperymentu/grafiki/bot.png"

# --- Ekran ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
DEFAULT_MONITOR_INDEX = 0 

# Obie wartości trzeba ZMIERZYĆ dla konkretnego stanowiska - jako jedyne w potoku
# nie dają się odczytać z danych ani z systemu, a błąd w nich przesuwa wszystkie
# cechy sakadowe w DVA względem tablicy STATS modelu.
# SCREEN_WIDTH_CM: szerokość aktywnej powierzchni matrycy (nie przekątna).
# VIEWING_DISTANCE_CM: odległość oczu od ekranu, dla GP3 zalecane 60-70 cm.
SCREEN_WIDTH_CM = 52.7
VIEWING_DISTANCE_CM = 65.0

# --- Wygląd bodźca tekstowego ---
BACKGROUND_COLOR = (40, 40, 40)
TEXT_COLOR = (255, 255, 255)
FONT_SIZE_PYGAME = 48
FONT_PATH = "C:/Windows/Fonts/Arial.ttf"
LINE_SPACING_MULTIPLIER = 1.8
VERTICAL_MARGIN_PERCENT = 0.1
HORIZONTAL_MARGIN_PERCENT = 0.15

# --- Treści prezentowane uczestnikowi ---
TEXT_FILE = "dane_do_eksperymentu/tekst_badawczy.txt"
TEXT_FILE_QUESTION = "dane_do_eksperymentu/pytanie_badawcze.txt"
TEXT_FILE_INSTRUCTION = "dane_do_eksperymentu/instrukcja_do_gry.txt"
BEHAVIORAL_RESULTS_FILENAME = "wyniki_behawioralne.csv"

# --- Zadanie kontrolne (gra z dronem): sakady do celu w losowych rogach ---
TARGET_WIDTH = 300
TARGET_HEIGHT = 300
TARGET_MAX_HEALTH = 100
TIME_TO_DESTROY_TARGET_S = 5.0
HEALTH_BAR_WIDTH = 400
HEALTH_BAR_HEIGHT = 30
HEALTH_BAR_COLOR_FULL = (0, 200, 0)
HEALTH_BAR_COLOR_EMPTY = (150, 0, 0)
SACCADE_TARGET_DURATION = 4000
SACCADE_TRIALS = 10

# --- Eyetracker ---
GAZEPOINT_HOST = '127.0.0.1'
GAZEPOINT_PORT = 4242
ONE_EURO_MIN_CUTOFF = 0.04
ONE_EURO_BETA = 0.9
EYETRACKER_FREQ = 150

# Margines siatki kalibracyjnej: punkty skrajne na 0.1 i 0.9 ekranu, środkowe
# na 0.5 - razem siatka 3x3, czyli kalibracja 9-punktowa.
CALIBRATION_MARGIN = 0.1


# === GEOMETRIA EKRANU NAGRANIA ===
#
# Geometria nie może być stałą modułu analizy, bo potok obsługuje dwa źródła
# o różnych ekranach: zbiór ETDD70 (1680x1050, współrzędne w pikselach tamtego
# ekranu) i własne stanowisko (piksele z góry tego pliku, współrzędne z GP3
# znormalizowane 0-1). Wchodzi do wyniku dwa razy: przez px_to_dva (cechy
# sakadowe modelu są w DVA) i przez xres/yres podawane do I2MC.

# Plik z geometrią zapisywany w folderze uczestnika - dzięki niemu nagranie
# opisuje samo siebie i analiza nie zależy od bieżącej treści tego pliku.
GEOMETRY_FILENAME = "parametry_ekranu.json"

# Zrzut bodźca z experiment_module - dla nagrań sprzed GEOMETRY_FILENAME jedyny
# ślad rzeczywistej rozdzielczości prezentacji.
STIMULUS_SCREENSHOT = "zrzut_ekranu_bodzca.png"


@dataclass(frozen=True)
class ScreenGeometry:
    # Komplet parametrów potrzebnych do przeliczenia wzroku na stopnie kąta
    # widzenia i do skonfigurowania I2MC. Pole 'source' trafia do raportu.
    width_px: int
    height_px: int
    width_cm: float
    viewing_distance_cm: float
    source: str = "nieznane źródło"

    @property
    def cm_per_px(self):
        return self.width_cm / self.width_px

    def px_to_dva(self, px_distance):
        # Piksele -> stopnie kąta widzenia, przez trójkąt oko-ekran.
        dist_cm = px_distance * self.cm_per_px
        return 2 * math.degrees(math.atan(dist_cm / (2 * self.viewing_distance_cm)))

    def describe(self):
        return (f"{self.width_px}x{self.height_px} px, szerokość ekranu "
                f"{self.width_cm:.1f} cm, odległość {self.viewing_distance_cm:.1f} cm "
                f"(źródło: {self.source})")


# Ekran użyty przy nagrywaniu ETDD70 - obowiązuje w analizie grupowej.
# Wymiary fizyczne są estymowane z rozdzielczości (1680x1050 to matryca 22" 16:10).
ETDD70_SCREEN = ScreenGeometry(
    width_px=1680,
    height_px=1050,
    width_cm=47.4,
    viewing_distance_cm=60.0,
    source="zbiór ETDD70 (parametry fizyczne estymowane)",
)


def _physical_params():
    # Walidacja jest tu celowo twarda: zerowa lub ujemna wartość dałaby wynik
    # policzony po cichu z bezsensownej skali.
    width_cm = float(SCREEN_WIDTH_CM)
    distance_cm = float(VIEWING_DISTANCE_CM)

    if width_cm <= 0 or distance_cm <= 0:
        raise ValueError(
            "SCREEN_WIDTH_CM i VIEWING_DISTANCE_CM w experiment_config.py muszą "
            "być dodatnie - bez nich nie da się przeliczyć pikseli na stopnie "
            "kąta widzenia.")

    return width_cm, distance_cm


def screen_from_config(width_px=None, height_px=None, source=None):
    # Rozdzielczość można nadpisać (np. odczytaną z systemu), parametry fizyczne
    # pochodzą zawsze z konfiguracji - nie da się ich zmierzyć programowo.
    width_cm, distance_cm = _physical_params()
    return ScreenGeometry(
        width_px=int(width_px if width_px else SCREEN_WIDTH),
        height_px=int(height_px if height_px else SCREEN_HEIGHT),
        width_cm=width_cm,
        viewing_distance_cm=distance_cm,
        source=source or "experiment_config.py",
    )


def detect_station_screen(monitor_index=0):
    # Geometria stanowiska w chwili nagrania. Rozdzielczość bierzemy z systemu,
    # bo to do niej - a nie do wpisu w konfiguracji - GP3 normalizuje POG.
    # Zwraca parę (geometria, szerokość z EDID lub None).
    width_px = height_px = None
    source = "experiment_config.py (nie odczytano parametrów monitora)"
    edid_width_cm = None

    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
        if not monitors:
            raise RuntimeError("nie znaleziono monitorów")

        monitor = monitors[monitor_index] if monitor_index < len(monitors) else monitors[0]
        width_px, height_px = int(monitor.width), int(monitor.height)
        source = f"screeninfo (monitor {monitor_index})"

        if monitor.width_mm:
            edid_width_cm = float(monitor.width_mm) / 10.0

    except Exception as e:
        print(f"[WARN] Nie udało się odczytać parametrów monitora ({e}). "
              f"Używam rozdzielczości z experiment_config.py.")

    if width_px and (width_px != SCREEN_WIDTH or height_px != SCREEN_HEIGHT):
        print(f"[WARN] Rozdzielczość monitora ({width_px}x{height_px}) różni się od "
              f"SCREEN_WIDTH/SCREEN_HEIGHT w experiment_config.py "
              f"({SCREEN_WIDTH}x{SCREEN_HEIGHT}). Do analizy zapisuję "
              f"rozdzielczość monitora, bo do niej normalizuje współrzędne GP3, "
              f"ale bodziec zostanie rozłożony według konfiguracji - zweryfikuj "
              f"ustawienia stanowiska.")

    screen = screen_from_config(width_px, height_px, source=source)

    # Szerokość z EDID bywa zaokrąglona albo pusta, więc nie zastępuje wartości
    # z konfiguracji - służy tylko do wychwycenia zmiany monitora.
    if edid_width_cm and edid_width_cm > 10.0:
        relative_diff = abs(edid_width_cm - screen.width_cm) / edid_width_cm
        if relative_diff > 0.05:
            print(f"[WARN] SCREEN_WIDTH_CM = {screen.width_cm:.1f} cm, a monitor "
                  f"zgłasza szerokość {edid_width_cm:.1f} cm (różnica "
                  f"{relative_diff * 100:.0f}%). Zmierz szerokość aktywnej "
                  f"powierzchni ekranu i popraw experiment_config.py - od tej "
                  f"wartości zależy przeliczenie cech na stopnie kąta widzenia.")

    return screen, edid_width_cm


def save_screen_geometry(screen, folder, edid_width_cm=None):
    # Geometria ląduje obok surowych danych uczestnika.
    payload = asdict(screen)
    if edid_width_cm:
        payload["width_cm_edid"] = round(edid_width_cm, 1)

    path = os.path.join(folder, GEOMETRY_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_screen_geometry(folder):
    # None oznacza "brak wiarygodnego zapisu" - i przy braku pliku, i przy pliku
    # niekompletnym. Jawny fallback jest lepszy niż połowiczne parametry.
    path = os.path.join(folder, GEOMETRY_FILENAME)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ScreenGeometry(
            width_px=int(data["width_px"]),
            height_px=int(data["height_px"]),
            width_cm=float(data["width_cm"]),
            viewing_distance_cm=float(data["viewing_distance_cm"]),
            source=f"{GEOMETRY_FILENAME} zapisany przy nagraniu "
                   f"({data.get('source', 'brak opisu')})",
        )
    except Exception as e:
        print(f"[WARN] Nie udało się odczytać pliku {path} ({e}). "
              f"Używam parametrów z experiment_config.py.")
        return None


def _stimulus_resolution(folder):
    # Rozdzielczość zrzutu bodźca = powierzchnia prezentacji w chwili nagrania.
    path = os.path.join(folder, STIMULUS_SCREENSHOT)
    if not os.path.exists(path):
        return None
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def screen_for_recording(folder):
    # Geometria dla analizy indywidualnej. Kolejno: plik zapisany przy nagraniu,
    # potem konfiguracja - z rozdzielczością skonfrontowaną ze zrzutem bodźca.
    screen = load_screen_geometry(folder)
    if screen is not None:
        return screen

    stimulus_size = _stimulus_resolution(folder)
    if stimulus_size and stimulus_size != (SCREEN_WIDTH, SCREEN_HEIGHT):
        print(f"[WARN] Brak pliku {GEOMETRY_FILENAME}, a zrzut ekranu bodźca ma "
              f"rozdzielczość {stimulus_size[0]}x{stimulus_size[1]} zamiast "
              f"{SCREEN_WIDTH}x{SCREEN_HEIGHT} z experiment_config.py. "
              f"Przyjmuję rozdzielczość ze zrzutu; parametry fizyczne ekranu "
              f"nadal pochodzą z konfiguracji - sprawdź, czy odpowiadają "
              f"stanowisku, na którym powstało nagranie.")
        return screen_from_config(
            stimulus_size[0], stimulus_size[1],
            source=f"{STIMULUS_SCREENSHOT} (rozdzielczość) + experiment_config.py "
                   f"(parametry fizyczne)")

    return screen_from_config(
        source=f"experiment_config.py (brak pliku {GEOMETRY_FILENAME})")
