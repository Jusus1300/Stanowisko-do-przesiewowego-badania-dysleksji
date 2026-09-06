# Stanowisko do przesiewowego badania dysleksji

System okulograficzny do przesiewowej oceny ryzyka dysleksji na podstawie ruchów oczu
podczas czytania. Repozytorium zawiera dwa niezależne, ale współpracujące potoki:

* **Stanowisko badawcze** – aplikacja w Pygame/Tkinter, która prowadzi uczestnika przez
  sesję (czytanie tekstu → pytanie weryfikacyjne → zadanie sakadowe) i rejestruje surowy
  sygnał z okulografu **Gazepoint GP3**.
* **System analizy** – segmentacja sygnału algorytmem **I2MC**, wyliczenie cech
  diagnostycznych ruchu oczu i ocena ryzyka modelem regresji logistycznej, wraz
  z narzędziami do etykietowania danych i retreningu modelu.

> **Zastrzeżenie.** Narzędzie ma charakter **przesiewowy i badawczy**. Wynik modelu nie
> jest diagnozą dysleksji i nie zastępuje opinii poradni psychologiczno-pedagogicznej.

---

## Spis treści

1. [Struktura repozytorium](#1-struktura-repozytorium)
2. [Wymagania](#2-wymagania)
3. [Instalacja](#3-instalacja)
4. [Przygotowanie plików bodźców](#4-przygotowanie-plików-bodźców)
5. [Uruchomienie eksperymentu](#5-uruchomienie-eksperymentu)
6. [Uruchomienie analizy](#6-uruchomienie-analizy)
7. [Etykietowanie wyników (`dodaj_etykiety.py`)](#7-etykietowanie-wyników-dodaj_etykietypy)
8. [Trening modelu (`model_trainer.py`)](#8-trening-modelu-model_trainerpy)
9. [Konfiguracja](#9-konfiguracja)
10. [Formaty plików](#10-formaty-plików)
11. [Model oceny ryzyka](#11-model-oceny-ryzyka)
12. [Najczęstsze problemy](#12-najczęstsze-problemy)
13. [Znane ograniczenia](#13-znane-ograniczenia)
14. [Źródła i licencje zależności](#14-źródła-i-licencje-zależności)

---

## 1. Struktura repozytorium

| Plik | Rola |
|---|---|
| `experiment_main.py` | **Punkt wejścia eksperymentu.** Sterownik sesji badawczej: identyfikator uczestnika, kalibracja, kolejne ekrany, zapis wyników behawioralnych. |
| `experiment_config.py` | Konfiguracja eksperymentu: ścieżki bodźców, rozdzielczość, parametry gry sakadowej, adres okulografu, parametry filtra. |
| `experiment_module.py` | Klasa `PygameExperiment` – ekrany w Pygame (czytanie, pytanie, instrukcja, gra sakadowa „stabilizacja bota”). |
| `gazepoint.py` | Klasa `GazeTracker` – klient Open Gaze API (TCP), kalibracja 9-punktowa, wątek zapisujący próbki do CSV, filtr One Euro na podgląd na żywo. |
| `tkinter_module.py` | Wszystkie okna Tkinter: powitania, wybór monitora, pole identyfikatora, GUI analizy, okno raportu, okna wyboru plików. |
| `analysis_main.py` | **Punkt wejścia analizy.** GUI z dwoma trybami: analiza indywidualna i grupowa. |
| `analysis_core.py` | Rdzeń analizy: wrapper I2MC, autodetekcja częstotliwości próbkowania, klasyfikacja zdarzeń FIX/SAC, wyliczanie cech, model ryzyka. |
| `analysis_individual.py` | Analiza pojedynczego nagrania z GP3: raport tekstowy + wykres ścieżki wzroku (*scanpath*). |
| `analysis_group.py` | Analiza wsadowa katalogu z nagraniami (format ETDD70), wieloprocesowa, zbiorczy CSV. |
| `dodaj_etykiety.py` | Dopisuje kolumnę `is_dyslexic` do wyników grupowych na podstawie pliku z etykietami. |
| `model_trainer.py` | Trening/retrening modelu regresji logistycznej z kroswalidacją; zapisuje `model_config.json`. |
| `model_config.json` | Wagi modelu (`intercept`, `coefs`) i tabela statystyk populacyjnych (`STATS`) do standaryzacji cech. |
| `requirements.txt` | Lista zależności Pythona. |

Katalogi `dane_do_eksperymentu/` (bodźce) i `dane_z_badan/` (nagrania) **nie są wersjonowane** –
trzeba je przygotować lokalnie (patrz [sekcja 4](#4-przygotowanie-plików-bodźców)).

### Przepływ danych

```
                    ┌──────────────────────┐
  uczestnik  ──────►│  experiment_main.py  │──►  dane_z_badan/<kryptonim>_<data>/
                    │  (Pygame + GP3)      │        czytanie_tekstu_dane_surowe.csv
                    └──────────────────────┘        zrzut_ekranu_bodzca.png
                                                    wyniki_behawioralne.csv  ...
                                                              │
                                                              ▼
                    ┌──────────────────────┐        #raport_<folder>.txt
                    │  analysis_main.py    │──────► #scanpath_<folder>.png
   zbiór ETDD70 ───►│  (I2MC + model)      │──────► #wyniki_grupowe.csv
                    └──────────────────────┘                  │
                                                              ▼
                                              dodaj_etykiety.py  ──►  is_dyslexic
                                                              │
                                                              ▼
                                              model_trainer.py  ──►  model_config.json
```

---

## 2. Wymagania

### 2.1 Sprzęt

* Okulograf **Gazepoint GP3** (lub zgodny, obsługujący **Open Gaze API**) wraz
  z oprogramowaniem **Gazepoint Control**.
* Monitor o rozdzielczości **1920 × 1080** (wartość domyślna w `experiment_config.py`).
  Obsługiwana jest praca wielomonitorowa – przy starcie pojawia się okno wyboru monitora.
* Sam **potok analizy** nie wymaga okulografu – wystarczą gotowe pliki CSV.

### 2.2 Oprogramowanie

* **Python 3.11** (sprawdzone na 3.11.15; biblioteki wymagają co najmniej 3.8).
* **Windows** dla części eksperymentalnej – `experiment_config.FONT_PATH` wskazuje
  `C:/Windows/Fonts/Arial.ttf`, a Gazepoint Control działa pod Windows.
  Przy braku tej czcionki program nie przerywa pracy, tylko używa domyślnej czcionki Pygame.
* **Tkinter** – w standardowym instalatorze Pythona dla Windows i macOS jest wbudowany.
  Na Linuksie trzeba go doinstalować z pakietów systemowych:

  ```bash
  sudo apt install python3-tk      # Debian / Ubuntu
  sudo dnf install python3-tkinter # Fedora
  ```

* **Gazepoint Control musi być uruchomiony** *przed* startem eksperymentu – aplikacja łączy
  się z nim po TCP na `127.0.0.1:4242`.

### 2.3 Biblioteki Python

| Biblioteka | Sprawdzona wersja | Używana przez | Do czego |
|---|---|---|---|
| `numpy` | 2.4.6 | wszystkie moduły analizy | operacje numeryczne, z-score, sigmoida |
| `pandas` | 3.0.5 | `analysis_*`, `dodaj_etykiety`, `model_trainer` | wczytywanie i zapis CSV, ramki danych |
| `matplotlib` | 3.11.1 | `analysis_individual`, `analysis_group` | wykresy ścieżki wzroku (*scanpath*) |
| `I2MC` | 2.2.8 | `analysis_core` | segmentacja fiksacji algorytmem I2MC |
| `scipy` | 1.17.1 | pośrednio (zależność `I2MC` i `scikit-learn`) | filtr Czebyszewa, interpolacja |
| `scikit-learn` | 1.9.0 | `model_trainer` | regresja logistyczna, standaryzacja, kroswalidacja |
| `pygame` | 2.6.1 | `experiment_module` | pełnoekranowa prezentacja bodźców, gra sakadowa |
| `Pillow` | 12.3.0 | `tkinter_module` | wczytanie i skalowanie tła okien Tkinter |
| `screeninfo` | 0.8.1 | `tkinter_module` | wykrywanie monitorów i ich geometrii |
| `OneEuroFilter` | 0.2.1 | `gazepoint` | wygładzanie kursora wzroku w podglądzie na żywo |

Biblioteki standardowe (bez instalacji): `tkinter`, `socket`, `threading`, `csv`, `json`,
`xml.etree.ElementTree`, `argparse`, `concurrent.futures`, `glob`, `os`, `sys`, `re`,
`math`, `random`, `time`, `datetime`, `traceback`.

---

## 3. Instalacja

```bash
git clone https://github.com/Jusus1300/stanowisko-do-przesiewowego-badania-dysleksji.git
cd stanowisko-do-przesiewowego-badania-dysleksji

# środowisko wirtualne
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

Bez pliku `requirements.txt` wystarczy:

```bash
pip install numpy pandas matplotlib scikit-learn I2MC OneEuroFilter pygame Pillow screeninfo
```

Sprawdzenie instalacji:

```bash
python -c "import numpy, pandas, matplotlib, sklearn, I2MC, OneEuroFilter, pygame, PIL, screeninfo, tkinter; print('OK')"
```

> **Ważne: wszystkie skrypty uruchamiaj z katalogu głównego repozytorium.**
> `analysis_core.py` i `model_trainer.py` odwołują się do `model_config.json` **ścieżką
> względną**, więc uruchomienie z innego katalogu spowoduje albo zejście modelu na wagi
> awaryjne wbudowane w kod, albo zapis nowej konfiguracji w niewłaściwym miejscu.

---

## 4. Przygotowanie plików bodźców

Eksperyment oczekuje katalogu `dane_do_eksperymentu/` obok skryptów (ścieżki definiuje
`experiment_config.py`):

```
dane_do_eksperymentu/
├── grafiki/
│   ├── tlo_kokpit.jpg          # tło ekranów (1920×1080), używane też przez okna Tkinter
│   └── bot.png                 # cel w zadaniu sakadowym (PNG z kanałem alfa)
├── tekst_badawczy.txt          # tekst do przeczytania (zadanie 1)
├── pytanie_badawcze.txt        # pytanie weryfikacyjne z odpowiedziami A / B
└── instrukcja_do_gry.txt       # instrukcja do zadania sakadowego
```

Wszystkie pliki tekstowe w **UTF-8**. Tekst jest automatycznie zawijany i skalowany do
rozmiaru ekranu, więc nie trzeba go ręcznie łamać na linie.

**Poprawną odpowiedzią na pytanie weryfikacyjne jest zawsze „A”** – zaszyte na sztywno
w `experiment_module.run_question_screen()`. Treść pytania trzeba ułożyć tak, aby
prawidłowy wariant był oznaczony literą A.

Brak plików nie przerywa eksperymentu: zamiast grafiki pojawi się jednolite tło, zamiast
tekstu komunikat „Błąd: Nie znaleziono pliku.”.

---

## 5. Uruchomienie eksperymentu

```bash
python experiment_main.py
```

### Przebieg sesji

1. **Wybór monitora** – tylko przy wykryciu więcej niż jednego ekranu.
2. **Kryptonim uczestnika** – np. `kadet_01`. Znaki inne niż alfanumeryczne, `_` i `-`
   są usuwane z nazwy katalogu.
3. **Ekran powitalny** → **kalibracja 9-punktowa** wykonywana przez Gazepoint Control
   (siatka 3 × 3 budowana z `CALIBRATION_MARGIN`). Po jej zakończeniu klikasz
   „Kalibracja Zakończona, Kontynuuj”.
4. **Zadanie 1 – czytanie tekstu.** Rejestracja startuje wraz z wyświetleniem tekstu,
   kończy się po naciśnięciu **Enter**. Zapisywany jest też zrzut ekranu bodźca
   (tło późniejszego wykresu ścieżki wzroku).
5. **Pytanie weryfikacyjne.** Odpowiedź klawiszem **A** lub **B**, mierzony czas reakcji,
   po czym informacja zwrotna.
6. **Instrukcja do gry** → **Enter**.
7. **Zadanie 2 – gra sakadowa.** Cel pojawia się w losowych rogach/centrum ekranu
   (do 10 prób po 4 s). Patrzenie na cel „stabilizuje bota” – pasek u góry rośnie;
   zadanie kończy się po napełnieniu paska lub wyczerpaniu prób.
8. **Ekran końcowy.**

**Klawisze:** `Enter` – dalej, `A` / `B` – odpowiedź, `Esc` – awaryjne przerwanie sesji
(okulograf jest wtedy poprawnie zamykany).

### Pliki wynikowe

Powstają w `dane_z_badan/<kryptonim>_<RRRR-MM-DD_GG-MM-SS>/`:

| Plik | Zawartość |
|---|---|
| `czytanie_tekstu_dane_surowe.csv` | surowe próbki wzroku z zadania czytania – **wejście analizy indywidualnej** |
| `zrzut_ekranu_bodzca.png` | zrzut ekranu z tekstem (tło wykresu *scanpath*) |
| `weryfikacja_dane_surowe.csv`, `weryfikacja_zdarzenia.csv` | nagranie i znaczniki z ekranu pytania |
| `gra_dane_surowe.csv`, `gra_zdarzenia.csv` | nagranie i znaczniki z zadania sakadowego |
| `wyniki_behawioralne.csv` | numer próby, odpowiedź, poprawność, czas reakcji |

Zadanie czytania celowo nie zapisuje pliku zdarzeń (nie ma w nim zdarzeń do oznaczenia).

---

## 6. Uruchomienie analizy

```bash
python analysis_main.py
```

Otwiera się pełnoekranowe okno z dwoma przyciskami. Zamknięcie – przycisk `✕`
w prawym górnym rogu.

### 6.1 Analiza indywidualna (pojedynczy plik)

Wskaż plik `czytanie_tekstu_dane_surowe.csv` z katalogu uczestnika. Program:

1. rozpoznaje, czy nagranie zawiera zapis **obuoczny** (`LPOG*` + `RPOG*`), czy tylko
   uśredniony punkt `BPOG*` – i odpowiednio przełącza I2MC w tryb obuoczny lub jednooczny;
2. wyznacza częstotliwość próbkowania z kolumny `TIME` (mediana odstępów między próbkami);
   przy braku kolumny używa `EYETRACKER_FREQ` z `experiment_config.py`;
3. oznacza próbki niepoprawne (poza zakresem 0–1 lub z flagą `POGV = 0`) jako `NaN`
   **osobno dla każdego oka** – wiersze nie są usuwane, żeby I2MC widział luki
   do interpolacji;
4. uruchamia segmentację I2MC, wylicza cechy i ocenę ryzyka.

Wyniki (w katalogu obok pliku wejściowego):

* okno raportu w GUI,
* `#raport_<nazwa_folderu>.txt` – ten sam raport na dysku,
* `#scanpath_<nazwa_folderu>.png` – ścieżka wzroku na tle bodźca
  (żółty punkt = pierwsza fiksacja, czerwony = ostatnia, rozmiar koła = czas trwania).

Jeśli w katalogu leży `wyniki_behawioralne.csv`, raport dołącza poprawność odpowiedzi
i czas reakcji.

### 6.2 Analiza grupowa (katalog)

Wskaż katalog z plikami pasującymi do wzorca **`Subject_*_raw.csv`** (format zbioru
**ETDD70**). Pliki są przetwarzane równolegle (`ProcessPoolExecutor`, jeden proces
na rdzeń). Wyniki:

* `#wyniki_grupowe.csv` – jeden wiersz na uczestnika (ocena ryzyka + wszystkie cechy),
* `<nazwa_pliku>_scanpath.png` dla każdego uczestnika (tło: opcjonalny `bodziec.jpg`
  w tym samym katalogu; pliki `*_scanpath.png` są w `.gitignore`).

### 6.3 Uruchomienie bez GUI

Oba potoki da się wywołać bezpośrednio z Pythona – przydatne na maszynie bez środowiska
graficznego lub przy przetwarzaniu wsadowym:

```python
# analiza indywidualna
import analysis_individual
print(analysis_individual.run_analysis("dane_z_badan/kadet_01_2026-09-06_10-00-00/czytanie_tekstu_dane_surowe.csv"))

# analiza grupowa (generate_plots=False przyspiesza przetwarzanie dużych zbiorów)
import analysis_group
print(analysis_group.run_analysis("sciezka/do/ETDD70", generate_plots=False))
```

---

## 7. Etykietowanie wyników (`dodaj_etykiety.py`)

Dopisuje do wyników grupowych kolumnę `is_dyslexic` (1/0) potrzebną do treningu modelu.

```bash
python dodaj_etykiety.py <wyniki_grupowe.csv> <dyslexia_class_label.csv> [plik_wyjsciowy.csv]
```

* **Argument 1** – wynik analizy grupowej (musi zawierać kolumnę `filename`).
* **Argument 2** – plik z etykietami; kolumny `subject_id`, `class_id`, `label`.
  Jeśli jest `class_id`, jest używany wprost; w przeciwnym razie etykieta powstaje
  z kolumny tekstowej `label` (`dyslexic` → 1).
* **Argument 3** (opcjonalny) – plik wyjściowy. **Pominięcie go nadpisuje plik wejściowy.**

Identyfikator uczestnika jest wyciągany z nazwy pliku – pierwsza liczba w `filename`
(np. `Subject_1003_T4_..._raw.csv` → `1003`). Uczestnicy bez dopasowanej etykiety są
wypisywani na konsolę, a w kolumnie dostają wartość pustą.

Przykład:

```bash
python dodaj_etykiety.py "#wyniki_grupowe.csv" dyslexia_class_label.csv wyniki_z_etykietami.csv
```

---

## 8. Trening modelu (`model_trainer.py`)

```bash
# tryb wsadowy
python model_trainer.py --input wyniki_z_etykietami.csv

# tryb interaktywny (okno wyboru pliku)
python model_trainer.py
```

Plik wejściowy musi zawierać pięć kolumn cech oraz `is_dyslexic`:

```
fix_reg_duration, fix_prog_duration, fix_reg_std, sac_prog_y_stab, sac_prog_dist_avg, is_dyslexic
```

Etykieta może być zapisana liczbowo (`0` / `1`) albo tekstowo
(`dyslexic`, `non-dyslexic`, `control`, `kontrola`, `dyslektyk`, …).

Przebieg:

1. odrzucenie rekordów z `segmentation_failed = True` (cechy są tam sztucznymi zerami)
   i wierszy z brakami danych;
2. `Pipeline(StandardScaler → LogisticRegression(C=np.inf))` – bez regularyzacji, żeby wagi
   trafiały do konfiguracji w niezmienionej postaci;
3. `RepeatedStratifiedKFold(n_splits=7, n_repeats=5, random_state=42)`; raportowane są
   trafność, czułość i swoistość ze zmiennością między foldami;
4. wagi oraz tabela `STATS` (średnie i odchylenia) są **uśredniane z 35 foldów**,
   a nie brane z osobnego dopasowania na całym zbiorze;
5. wypisywane jest porównanie starych i nowych wartości;
6. zapis do `model_config.json` (**w bieżącym katalogu roboczym** – uruchamiaj z katalogu
   głównego repozytorium).

> **Po każdym retreningu** trzeba ręcznie przepisać nowe wagi i tabelę `STATS`
> do zestawu awaryjnego w `analysis_core.calculate_risk_score()`. Ten zestaw jest używany
> tylko wtedy, gdy `model_config.json` nie istnieje – rozjazd między nimi po cichu zmienia
> wynik modelu, bez żadnego sygnału dla operatora.

---

## 9. Konfiguracja

### 9.1 `experiment_config.py`

| Parametr | Domyślnie | Znaczenie |
|---|---|---|
| `DATA_FOLDER` | `dane_z_badan` | katalog na nagrania |
| `SCREEN_WIDTH`, `SCREEN_HEIGHT` | `1920`, `1080` | rozdzielczość okna pełnoekranowego |
| `DEFAULT_MONITOR_INDEX` | `0` | monitor wybrany domyślnie |
| `FONT_PATH` | `C:/Windows/Fonts/Arial.ttf` | czcionka bodźców (fallback: czcionka Pygame) |
| `FONT_SIZE_PYGAME` | `48` | wyjściowy rozmiar czcionki (zmniejszany, aż tekst się zmieści) |
| `TEXT_FILE`, `TEXT_FILE_QUESTION`, `TEXT_FILE_INSTRUCTION` | `dane_do_eksperymentu/*.txt` | pliki bodźców |
| `TARGET_MAX_HEALTH`, `TIME_TO_DESTROY_TARGET_S` | `100`, `5.0` | ile sekund patrzenia napełnia pasek |
| `SACCADE_TRIALS`, `SACCADE_TARGET_DURATION` | `10`, `4000` ms | liczba i czas trwania prób sakadowych |
| `GAZEPOINT_HOST`, `GAZEPOINT_PORT` | `127.0.0.1`, `4242` | adres Open Gaze API |
| `EYETRACKER_FREQ` | `150` | zapasowa częstotliwość okulografu (Hz) |
| `ONE_EURO_MIN_CUTOFF`, `ONE_EURO_BETA` | `0.04`, `0.9` | filtr One Euro – dotyczy **wyłącznie** podglądu na żywo, nie zapisu |
| `CALIBRATION_MARGIN` | `0.1` | margines siatki 3 × 3 → kalibracja 9-punktowa |

### 9.2 `analysis_core.py`

| Stała | Domyślnie | Znaczenie |
|---|---|---|
| `SCREEN_WIDTH`, `SCREEN_HEIGHT` | `1680`, `1050` | geometria ekranu przyjmowana przez potok analizy (`xres`/`yres` dla I2MC, skalowanie znormalizowanych współrzędnych GP3) |
| `SCREEN_WIDTH_CM`, `VIEWING_DISTANCE_CM` | `47.4`, `60.0` | parametry fizyczne do przeliczenia pikseli na stopnie kąta widzenia (DVA) |
| `GROUP_EXPERIMENT_FREQ` | `250` | zapasowa częstotliwość dla analizy grupowej (Hz) |
| `INTERP_MAX_GAP_MS` | `100` | najdłuższa luka w sygnale, którą I2MC może interpolować |
| `WINDOW_SIZE_MS` | `200` | okno grupowania 2-means |
| `I2MC_RANDOM_SEED` | `42` | ziarno RNG – bez niego ten sam plik daje przy każdym uruchomieniu inny wynik (obserwowany rozstęp oceny ryzyka do 0,13); `None` przywraca losowość |

> **Uwaga przy własnych nagraniach.** Stałe `SCREEN_WIDTH`/`SCREEN_HEIGHT` w `analysis_core.py`
> (1680 × 1050) odpowiadają geometrii zbioru ETDD70, natomiast stanowisko eksperymentalne
> pracuje w 1920 × 1080. Analizując własne nagrania z GP3, dopasuj te stałe (a także
> `SCREEN_WIDTH_CM` i `VIEWING_DISTANCE_CM`) do swojego stanowiska – od nich zależy
> przeliczanie na DVA, a więc wartości cech sakadowych i wynik modelu.

### 9.3 `model_config.json`

Odczytywany przy każdej ocenie ryzyka:

```json
{
  "weights": { "intercept": 0.295, "coefs": [1.509, 1.162, -0.115, 0.720, -0.139] },
  "STATS": { "fix_reg_duration": { "mean": 337.56, "std": 72.41 }, "...": {} }
}
```

Kolejność w `coefs` odpowiada kolejności cech:
`fix_reg_duration`, `fix_prog_duration`, `fix_reg_std`, `sac_prog_y_stab`, `sac_prog_dist_avg`.

---

## 10. Formaty plików

### 10.1 Nagranie z GP3 (`*_dane_surowe.csv`)

| Kolumna | Opis |
|---|---|
| `PC_TIME` | znacznik czasu PC zsynchronizowany z zegarem okulografu |
| `TIME`, `TIME_TICK` | czas i licznik taktów okulografu |
| `LPOGX`, `LPOGY`, `LPOGV` | punkt spojrzenia oka **lewego** (0–1) i flaga poprawności |
| `RPOGX`, `RPOGY`, `RPOGV` | punkt spojrzenia oka **prawego** i flaga poprawności |
| `BPOGX`, `BPOGY`, `BPOGV` | punkt uśredniony przez okulograf (podgląd na żywo, zapas) |

Zapis obu oczu jest włączany komendami `ENABLE_SEND_POG_LEFT` / `ENABLE_SEND_POG_RIGHT`;
bez nich I2MC nie ma dwóch niezależnych sygnałów i traci deklarowaną odporność na szum.
Starsze nagrania zawierające tylko `BPOG*` są nadal obsługiwane – potok schodzi wtedy
do trybu jednoocznego.

### 10.2 Nagranie ETDD70 (`Subject_*_raw.csv`)

Kolumny `time`, `gaze_x_left`, `gaze_y_left` oraz (opcjonalnie) `gaze_x_right`,
`gaze_y_right`, we współrzędnych pikselowych. Próbki o współrzędnych `≤ 1` są traktowane
jako utrata sygnału.

### 10.3 `wyniki_behawioralne.csv`

`NumerProby, Odpowiedz, CzyPoprawna, CzasReakcji_s`

### 10.4 `#wyniki_grupowe.csv`

`filename, score, risk_group` + wszystkie cechy: `fix_prog_duration`, `fix_reg_duration`,
`fix_reg_std`, `fix_dur_std`, `sac_prog_pos_x_mean`, `sac_prog_dist_avg`, `sac_prog_range`,
`sac_prog_y_stab`, `sac_reg_y_stab`, `segmentation_failed`.

---

## 11. Model oceny ryzyka

### Potok analizy

1. **Przygotowanie sygnału** – skalowanie do pikseli, oznaczenie niepoprawnych próbek jako
   `NaN` osobno dla każdego oka (wiersze zostają, żeby oś czasu się nie przesunęła).
2. **Segmentacja I2MC** (*Identification by Two-Means Clustering*) – wykrycie fiksacji;
   przy dwóch oczach każde jest grupowane niezależnie, a wagi są uśredniane.
3. **Rekonstrukcja zdarzeń** – lista `FIX` (fiksacje) i `SAC` (sakady odtworzone jako
   przesunięcia między kolejnymi fiksacjami).
4. **Cechy diagnostyczne** – podział na progresje (ruch w prawo) i regresje (ruch w lewo).
5. **Ocena ryzyka** – standaryzacja (z-score) względem tabeli `STATS`, model logistyczny.

### Cechy wejściowe modelu

| Cecha | Jednostka | Opis |
|---|---|---|
| `fix_reg_duration` | ms | średni czas fiksacji po regresji |
| `fix_prog_duration` | ms | średni czas fiksacji po progresji |
| `fix_reg_std` | ms | odchylenie standardowe czasów fiksacji po regresjach |
| `sac_prog_y_stab` | DVA | średnia zmiana pozycji Y w trakcie sakad progresywnych (stabilność linii) |
| `sac_prog_dist_avg` | DVA | średnia amplituda sakad progresywnych |

### Wynik

```
Z = intercept + Σ βᵢ · z-score(cechaᵢ)
P = 1 / (1 + e^(−Z))
```

`P > 0.5` → **„Wysokie ryzyko”**, w przeciwnym razie **„Niskie ryzyko”**.

Jeśli I2MC nie wykryje ani jednej fiksacji, cechy są sztucznymi zerami – potok zwraca wtedy
jawny status **„BŁĄD SEGMENTACJI – wynik nieokreślony”** zamiast fałszywie niskiego ryzyka.

Aktualne wagi pochodzą z retreningu na zbiorze **ETDD70** (70 uczestników, zadanie
*T4 – Meaningful Text*) z etykietami `is_dyslexic`.

---

## 12. Najczęstsze problemy

| Objaw | Przyczyna i rozwiązanie |
|---|---|
| `[BŁĄD KRYTYCZNY] Upewnij się, że oprogramowanie Gazepoint Control jest uruchomione.` | Gazepoint Control nie działa albo nasłuchuje na innym porcie – sprawdź `GAZEPOINT_HOST` / `GAZEPOINT_PORT`. |
| `[WARN] Gazepoint Control nie odpowiada na komendy SET` | Ta wersja Gazepoint Control nie potwierdza poleceń. Program działa dalej, ale nie zweryfikuje ustawień – liczbę punktów kalibracji sprawdź ręcznie w oknie Gazepoint Control. |
| `[BŁĄD] Gazepoint przyjął tylko N/9 punktów` | Kalibracja **nie jest** 9-punktowa – powtórz konfigurację przed rozpoczęciem badania. |
| `ModuleNotFoundError: No module named 'tkinter'` | Doinstaluj `python3-tk` (patrz [sekcja 2.2](#22-oprogramowanie)). |
| `Nie znaleziono plików pasujących do wzorca 'Subject_*_raw.csv'` | Analiza grupowa oczekuje dokładnie takiego wzorca nazw – zmień nazwy plików albo wskaż właściwy katalog. |
| `Ostrzeżenie: Brak pliku 'model_config.json'` | Skrypt uruchomiony spoza katalogu głównego repozytorium (albo plik usunięty) – model zszedł na wagi awaryjne z kodu. |
| `BŁĄD SEGMENTACJI – wynik nieokreślony` | I2MC nie wykrył fiksacji: za krótkie nagranie, zbyt duża utrata sygnału albo błędna kalibracja. Nagranie nadaje się do odrzucenia. |
| Wykres *scanpath* z napisem „Brak pliku tła” | Brak `zrzut_ekranu_bodzca.png` (analiza indywidualna) lub `bodziec.jpg` (analiza grupowa) w katalogu z danymi. Wykres i tak powstaje. |
| `[WARN] Błąd ładowania grafiki` | Brak plików w `dane_do_eksperymentu/grafiki/` – eksperyment działa na jednolitym tle. |

---

## 13. Znane ograniczenia

* **Narzędzie przesiewowe, nie diagnostyczne.** Wynik to prawdopodobieństwo z modelu
  wytrenowanego na 70 uczestnikach jednego zbioru; nie jest diagnozą.
* **Wagi awaryjne w `analysis_core.py` są synchronizowane ręcznie.** Po retreningu trzeba
  je przepisać, inaczej brak `model_config.json` cicho zmieni wynik.
* **Stałe ekranu w analizie odpowiadają zbiorowi ETDD70** (1680 × 1050), nie stanowisku
  eksperymentalnemu (1920 × 1080) – patrz [sekcja 9.2](#92-analysis_corepy).
* **I2MC zakłada równomierne próbkowanie.** Wykryta częstotliwość służy tylko do wyliczenia
  jednego skalara (okresu próbkowania); do segmentacji używana jest syntetyczna, równomierna
  oś czasu budowana z indeksu wierszy.
* **Sakady są rekonstruowane, nie mierzone** – modelowane jako natychmiastowe przesunięcia
  między kolejnymi fiksacjami (`duration_samples = 0`), więc czas ich trwania nie jest
  wielkością mierzoną.
* **Poprawna odpowiedź na pytanie weryfikacyjne jest zaszyta na sztywno jako „A”.**
* **Raport indywidualny opisuje pozycje 4 i 5 jako „px”**, choć `sac_prog_dist_avg`
  i `sac_prog_range` są wyrażone w stopniach kąta widzenia (DVA) – to jedynie etykieta
  w tekście raportu, wartości w CSV i w modelu są w DVA.
* **Filtr One Euro działa wyłącznie na podglądzie na żywo** w grze sakadowej; do plików CSV
  trafia sygnał niefiltrowany.

---

## 14. Źródła i licencje zależności

* **I2MC** – Hessels, R. S., Niehorster, D. C., Kemner, C., & Hooge, I. T. C. (2017).
  *Noise-robust fixation detection in eye movement data: Identification by two-means
  clustering (I2MC).* Behavior Research Methods, 49(5), 1802–1823.
  Implementacja: <https://github.com/dcnieho/I2MC_Python> (MIT).
* **One Euro Filter** – Casiez, G., Roussel, N., & Vogel, D. (2012).
  *1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in Interactive Systems.*
  Implementacja: pakiet `OneEuroFilter` (BSD-3-Clause).
* **Open Gaze API** – protokół sterowania okulografami Gazepoint (GP3).
* **ETDD70** – publicznie dostępny zbiór nagrań okulograficznych dla badań nad dysleksją
  (70 uczestników, zadania T1–T5); potok korzysta z zadania *T4 – Meaningful Text*.
