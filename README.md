# Stanowisko do przesiewowego badania dysleksji

System okulograficzny do przesiewowej oceny ryzyka dysleksji na podstawie ruchów oczu
podczas czytania.

## Wymagania

* Python 3.11 (min. 3.8)
* Okulograf Gazepoint GP3 (lub zgodny, obsługujący Open Gaze API) z uruchomionym
  oprogramowaniem Gazepoint Control — wymagany tylko do części eksperymentalnej;
  sam potok analizy działa na gotowych plikach CSV
* Tkinter — wbudowany w standardowy instalator Pythona (Windows/macOS); na Linuksie:

  ```bash
  sudo apt install python3-tk      # Debian / Ubuntu
  sudo dnf install python3-tkinter # Fedora
  ```

### Biblioteki Python

```
numpy
pandas
matplotlib
scikit-learn
I2MC
scipy
pygame
Pillow
screeninfo
OneEuroFilter
```

## Instalacja

```bash
git clone https://github.com/Jusus1300/stanowisko-do-przesiewowego-badania-dysleksji.git
cd stanowisko-do-przesiewowego-badania-dysleksji

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

Wszystkie skrypty uruchamiaj z katalogu głównego repozytorium.

## Konfiguracja stanowiska

Przed pierwszym badaniem ustaw w `experiment_config.py` parametry ekranu, na którym
prezentowany jest bodziec:

| Parametr | Znaczenie |
| --- | --- |
| `SCREEN_WIDTH`, `SCREEN_HEIGHT` | rozdzielczość ekranu w pikselach |
| `SCREEN_WIDTH_CM` | zmierzona szerokość aktywnej powierzchni matrycy (nie przekątna) |
| `VIEWING_DISTANCE_CM` | odległość oczu badanego od ekranu (dla GP3 zwykle 60-70 cm) |

Te cztery liczby opisują geometrię nagrania i decydują o przeliczeniu współrzędnych
wzroku na stopnie kąta widzenia (DVA), w których wyrażone są cechy sakadowe modelu.
Błąd w nich przesuwa wynik systematycznie dla wszystkich badanych, dlatego szerokość
ekranu i odległość trzeba zmierzyć, a nie oszacować.

`experiment_main.py` zapisuje użytą geometrię w folderze uczestnika jako
`parametry_ekranu.json` (rozdzielczość odczytana z systemu, parametry fizyczne
z konfiguracji), więc nagranie opisuje samo siebie i późniejsza zmiana konfiguracji
nie zmienia interpretacji wcześniejszych danych.

## Uruchomienie eksperymentu

```bash
python experiment_main.py
```

Wymaga katalogu `dane_do_eksperymentu/` obok skryptów, ze ścieżkami zdefiniowanymi
w `experiment_config.py`.

## Uruchomienie analizy

```bash
python analysis_main.py
```

Otwiera GUI z wyborem analizy indywidualnej (pojedynczy plik CSV z nagrania) lub
grupowej (katalog z plikami `Subject_*_raw.csv`).

Geometrię ekranu każda z analiz bierze z odpowiedniego źródła (patrz sekcja
GEOMETRIA EKRANU NAGRANIA w `experiment_config.py`):

* analiza indywidualna - z pliku `parametry_ekranu.json` w folderze nagrania,
  a gdy go brak (nagrania sprzed wprowadzenia tego pliku) - z `experiment_config.py`,
  z ostrzeżeniem, jeśli zrzut ekranu bodźca ma inną rozdzielczość niż konfiguracja;
* analiza grupowa - z parametrów zbioru ETDD70 (1680x1050), bo pliki
  `Subject_*_raw.csv` zawierają współrzędne w pikselach tamtego ekranu.

Użyta geometria trafia do nagłówka raportu indywidualnego, więc widać w nim, na
jakich parametrach policzono wynik.

## Etykietowanie wyników

```bash
python dodaj_etykiety.py <wyniki_grupowe.csv> <dyslexia_class_label.csv> [plik_wyjsciowy.csv]
```

## Trening modelu

```bash
python model_trainer.py --input wyniki_grupowe_is_dyslexic.csv
```

Plik `wyniki_grupowe_is_dyslexic.csv` zawiera dane, na których był trenowany aktualny
model (wagi w `model_config.json`).
