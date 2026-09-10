# Ustawienia Główne
DATA_FOLDER = "dane_z_badan"

# Ścieżki do Plików Graficznych
BACKGROUND_IMG = "dane_do_eksperymentu/grafiki/tlo_kokpit.jpg"
TARGET_IMG = "dane_do_eksperymentu/grafiki/bot.png"

# Ustawienia Ekranu i Grafiki
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
DEFAULT_MONITOR_INDEX = 0 

# Fizyczne parametry stanowiska. Razem z rozdzielczością powyżej opisują
# geometrię, w której powstaje nagranie, i są używane przez analizę do
# przeliczenia pikseli na stopnie kąta widzenia (patrz screen_geometry.py).
# Obie wartości trzeba ZMIERZYĆ dla konkretnego stanowiska - są to jedyne
# parametry potoku, których nie da się odczytać z danych ani z systemu, a
# błąd w nich przesuwa wszystkie cechy sakadowe względem tablicy STATS modelu
# (np. 10% za mała szerokość ekranu zaniża sac_prog_dist_avg o ~10%).
#
# SCREEN_WIDTH_CM: szerokość aktywnej powierzchni matrycy (nie przekątna
#   i nie szerokość obudowy). Wartość domyślna odpowiada typowemu monitorowi
#   23,8" w formacie 16:9.
# VIEWING_DISTANCE_CM: odległość oczu badanego od ekranu; dla Gazepoint GP3
#   zalecany zakres to 60-70 cm.
SCREEN_WIDTH_CM = 52.7
VIEWING_DISTANCE_CM = 65.0

BACKGROUND_COLOR = (40, 40, 40)
TEXT_COLOR = (255, 255, 255)
FONT_SIZE_PYGAME = 48
FONT_PATH = "C:/Windows/Fonts/Arial.ttf"
LINE_SPACING_MULTIPLIER = 1.8
VERTICAL_MARGIN_PERCENT = 0.1
HORIZONTAL_MARGIN_PERCENT = 0.15

# Ustawienia Eksperymentu
TEXT_FILE = "dane_do_eksperymentu/tekst_badawczy.txt"
TEXT_FILE_QUESTION = "dane_do_eksperymentu/pytanie_badawcze.txt"
TEXT_FILE_INSTRUCTION = "dane_do_eksperymentu/instrukcja_do_gry.txt"
BEHAVIORAL_RESULTS_FILENAME = "wyniki_behawioralne.csv"

# Ustawienia Zadania Kontrolnego (Gra z Dronem)
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

# Ustawienia Eyetrackera (dla eksperymentu)
GAZEPOINT_HOST = '127.0.0.1'
GAZEPOINT_PORT = 4242
ONE_EURO_MIN_CUTOFF = 0.04
ONE_EURO_BETA = 0.9
EYETRACKER_FREQ = 150

# Margines siatki kalibracyjnej we współrzędnych znormalizowanych: punkty
# skrajne trafiają na 0.1 i 0.9 szerokości/wysokości ekranu, środkowe na 0.5.
# Z tego powstaje siatka 3x3, czyli kalibracja 9-punktowa.
CALIBRATION_MARGIN = 0.1

