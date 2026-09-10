# Geometria ekranu, na którym powstało nagranie.
#
# Potok analizy przetwarza dane z dwóch źródeł o różnej geometrii:
#
#   * zbiór ETDD70 (analiza grupowa) - ekran 1680x1050, współrzędne zapisane
#     już w pikselach tamtego ekranu,
#   * własne stanowisko (analiza indywidualna) - ekran opisany w
#     experiment_config.py, współrzędne z GP3 znormalizowane do zakresu 0-1.
#
# Geometria nie może być więc globalną stałą modułu analizy: decyduje o niej
# nagranie, a nie plik z kodem. Wchodzi ona do wyniku dwa razy i za każdym
# razem zmienia liczby, które trafiają do modelu:
#
#   1. przeliczenie pikseli na stopnie kąta widzenia (px_to_dva) - zależy od
#      szerokości ekranu w pikselach i centymetrach oraz od odległości oczu
#      od ekranu; cechy sakadowe modelu (sac_prog_dist_avg, sac_prog_y_stab)
#      są wyrażone właśnie w DVA,
#   2. parametry xres/yres podawane do I2MC - z nich algorytm liczy m.in.
#      próg interpolacji luk (maxdisp) i skalę grupowania.
#
# Podstawienie geometrii ETDD70 pod nagranie z własnego stanowiska (1920x1080)
# dawało 14% błędu skali na osi X i inną skalę na osi Y, czyli systematyczne
# przesunięcie wszystkich cech sakadowych względem tablicy STATS modelu.

import json
import math
import os
from dataclasses import dataclass, asdict

import experiment_config as cfg

# Nazwa pliku z parametrami ekranu, zapisywanego w folderze uczestnika przez
# experiment_main.py. Dzięki niemu nagranie opisuje samo siebie i analiza nie
# musi zakładać, że konfiguracja stanowiska nie zmieniła się od czasu badania.
GEOMETRY_FILENAME = "parametry_ekranu.json"

# Zrzut ekranu bodźca zapisywany przez experiment_module.run_reading_screen.
# Dla starszych nagrań, sprzed wprowadzenia GEOMETRY_FILENAME, jest to jedyny
# ślad rzeczywistej rozdzielczości prezentacji.
STIMULUS_SCREENSHOT = "zrzut_ekranu_bodzca.png"


@dataclass(frozen=True)
class ScreenGeometry:

    # Komplet parametrów potrzebnych do przeliczenia współrzędnych wzroku na
    # stopnie kąta widzenia i do skonfigurowania I2MC.
    #
    # width_cm to szerokość *aktywnej powierzchni* matrycy (nie przekątna
    # i nie szerokość obudowy), viewing_distance_cm - odległość oczu badanego
    # od ekranu.

    width_px: int
    height_px: int
    width_cm: float
    viewing_distance_cm: float
    source: str = "nieznane źródło"

    @property
    def cm_per_px(self):
        return self.width_cm / self.width_px

    def px_to_dva(self, px_distance):
        # Konwertuje dystans w pikselach na stopnie kąta widzenia (DVA).
        dist_cm = px_distance * self.cm_per_px
        return 2 * math.degrees(math.atan(dist_cm / (2 * self.viewing_distance_cm)))

    def describe(self):
        return (f"{self.width_px}x{self.height_px} px, szerokość ekranu "
                f"{self.width_cm:.1f} cm, odległość {self.viewing_distance_cm:.1f} cm "
                f"(źródło: {self.source})")


# Ekran użyty przy nagrywaniu zbioru ETDD70 - obowiązuje w analizie grupowej,
# bo pliki Subject_*_raw.csv zawierają współrzędne w pikselach tamtego ekranu.
# Parametry fizyczne są estymowane z rozdzielczości (1680x1050 to matryca 22"
# w formacie 16:10).
ETDD70_SCREEN = ScreenGeometry(
    width_px=1680,
    height_px=1050,
    width_cm=47.4,
    viewing_distance_cm=60.0,
    source="zbiór ETDD70 (parametry fizyczne estymowane)",
)


def _physical_params():
    # Parametry fizyczne stanowiska z experiment_config, z walidacją: błędnie
    # ustawiona szerokość lub odległość przelicza się wprost na przesunięcie
    # wszystkich cech w DVA, więc lepiej przerwać niż liczyć po cichu.
    width_cm = float(cfg.SCREEN_WIDTH_CM)
    distance_cm = float(cfg.VIEWING_DISTANCE_CM)

    if width_cm <= 0 or distance_cm <= 0:
        raise ValueError(
            "SCREEN_WIDTH_CM i VIEWING_DISTANCE_CM w experiment_config.py muszą "
            "być dodatnie - bez nich nie da się przeliczyć pikseli na stopnie "
            "kąta widzenia.")

    return width_cm, distance_cm


def config_screen(width_px=None, height_px=None, source=None):

    # Geometria stanowiska wynikająca z experiment_config.py. Rozdzielczość
    # można nadpisać (np. rzeczywistą rozdzielczością monitora odczytaną z
    # systemu), parametry fizyczne pochodzą zawsze z konfiguracji - nie da się
    # ich zmierzyć programowo.

    width_cm, distance_cm = _physical_params()
    return ScreenGeometry(
        width_px=int(width_px if width_px else cfg.SCREEN_WIDTH),
        height_px=int(height_px if height_px else cfg.SCREEN_HEIGHT),
        width_cm=width_cm,
        viewing_distance_cm=distance_cm,
        source=source or "experiment_config.py",
    )


def detect_station_screen(monitor_index=0):

    # Geometria stanowiska w chwili nagrania. Rozdzielczość bierzemy z systemu
    # (screeninfo), bo to ona - a nie wpis w konfiguracji - decyduje, do czego
    # GP3 normalizuje współrzędne POG: okulograf kalibruje się do całej
    # powierzchni monitora. Rozjazd między monitorem a experiment_config
    # oznacza dodatkowo źle rozłożony bodziec, więc jest zgłaszany.
    #
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

    if width_px and (width_px != cfg.SCREEN_WIDTH or height_px != cfg.SCREEN_HEIGHT):
        print(f"[WARN] Rozdzielczość monitora ({width_px}x{height_px}) różni się od "
              f"SCREEN_WIDTH/SCREEN_HEIGHT w experiment_config.py "
              f"({cfg.SCREEN_WIDTH}x{cfg.SCREEN_HEIGHT}). Do analizy zapisuję "
              f"rozdzielczość monitora, bo do niej normalizuje współrzędne GP3, "
              f"ale bodziec zostanie rozłożony według konfiguracji - zweryfikuj "
              f"ustawienia stanowiska.")

    screen = config_screen(width_px, height_px, source=source)

    # Szerokość z EDID bywa zaokrąglona albo pusta, więc nie zastępuje nią
    # wartości z konfiguracji - służy wyłącznie do wychwycenia sytuacji, w
    # której operator zmienił monitor i zapomniał poprawić SCREEN_WIDTH_CM.
    if edid_width_cm and edid_width_cm > 10.0:
        relative_diff = abs(edid_width_cm - screen.width_cm) / edid_width_cm
        if relative_diff > 0.05:
            print(f"[WARN] SCREEN_WIDTH_CM = {screen.width_cm:.1f} cm, a monitor "
                  f"zgłasza szerokość {edid_width_cm:.1f} cm (różnica "
                  f"{relative_diff * 100:.0f}%). Zmierz szerokość aktywnej "
                  f"powierzchni ekranu i popraw experiment_config.py - od tej "
                  f"wartości zależy przeliczenie cech na stopnie kąta widzenia.")

    return screen, edid_width_cm


def save(screen, folder, edid_width_cm=None):

    # Zapisuje geometrię obok surowych danych uczestnika, żeby analiza mogła
    # odtworzyć warunki nagrania niezależnie od bieżącej zawartości
    # experiment_config.py.

    payload = asdict(screen)
    if edid_width_cm:
        payload["width_cm_edid"] = round(edid_width_cm, 1)

    path = os.path.join(folder, GEOMETRY_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load(folder):

    # Odczytuje geometrię zapisaną przy nagraniu. Zwraca None, gdy pliku nie
    # ma (nagranie sprzed wprowadzenia GEOMETRY_FILENAME) albo gdy jest
    # niekompletny - w obu przypadkach lepszy jest jawny fallback niż
    # połowiczne dane.

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
    # Rozdzielczość zrzutu ekranu bodźca - odpowiada powierzchni prezentacji
    # w chwili nagrania.
    path = os.path.join(folder, STIMULUS_SCREENSHOT)
    if not os.path.exists(path):
        return None
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def for_recording(folder):

    # Geometria, której ma użyć analiza indywidualna dla nagrania z podanego
    # folderu. Kolejność źródeł: plik zapisany przy nagraniu, potem
    # experiment_config, przy czym rozdzielczość jest jeszcze konfrontowana ze
    # zrzutem ekranu bodźca - dla starszych nagrań to jedyny zapis tego, na
    # jakim ekranie faktycznie prezentowano tekst.

    screen = load(folder)
    if screen is not None:
        return screen

    stimulus_size = _stimulus_resolution(folder)
    if stimulus_size and stimulus_size != (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT):
        print(f"[WARN] Brak pliku {GEOMETRY_FILENAME}, a zrzut ekranu bodźca ma "
              f"rozdzielczość {stimulus_size[0]}x{stimulus_size[1]} zamiast "
              f"{cfg.SCREEN_WIDTH}x{cfg.SCREEN_HEIGHT} z experiment_config.py. "
              f"Przyjmuję rozdzielczość ze zrzutu; parametry fizyczne ekranu "
              f"nadal pochodzą z konfiguracji - sprawdź, czy odpowiadają "
              f"stanowisku, na którym powstało nagranie.")
        return config_screen(
            stimulus_size[0], stimulus_size[1],
            source=f"{STIMULUS_SCREENSHOT} (rozdzielczość) + experiment_config.py "
                   f"(parametry fizyczne)")

    return config_screen(
        source=f"experiment_config.py (brak pliku {GEOMETRY_FILENAME})")
