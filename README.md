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
