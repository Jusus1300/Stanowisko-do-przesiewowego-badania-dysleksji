# Ustawienia Główne
DATA_FOLDER = "dane_z_badan"

# Ścieżki do Plików Graficznych
BACKGROUND_IMG = "dane_do_eksperymentu/grafiki/tlo_kokpit.jpg"
TARGET_IMG = "dane_do_eksperymentu/grafiki/bot.png"

# Ustawienia Ekranu i Grafiki
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
DEFAULT_MONITOR_INDEX = 0 
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

