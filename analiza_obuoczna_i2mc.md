# Analiza wprowadzenia obuocznej segmentacji I2MC

Dokument odpowiada na dwa pytania: (1) czy postawiona diagnoza — że obecny potok
analizuje jedno oko, a obuoczność I2MC nie jest wykorzystywana — jest prawdziwa,
oraz (2) czy przejście na rzeczywistą analizę obuoczną zmieniłoby wyniki końcowe.

Wszystkie liczby pochodzą ze skryptu `porownanie_obuoczne.py` uruchomionego na
pięciu uczestnikach ETDD70 (T4 Meaningful Text: 1075, 1082, 1090, 1095, 1109),
po 12 powtórzeń na wariant, łącznie 240 przebiegów I2MC.

---

## 1. Potwierdzenie diagnozy

`analysis_core.apply_i2mc_segmentation` (w. 118–132) buduje słownik wejściowy,
w którym `L_X`/`L_Y` i `R_X`/`R_Y` wskazują na **tę samą tablicę** — sygnał oka
lewego pobrany w `analysis_group.process_single_subject` z kolumn `gaze_x_left`
i `gaze_y_left`. Kolumny `gaze_x_right`/`gaze_y_right` nie są wczytywane w ogóle.

W bibliotece I2MC (wersja 2.2.8) taki słownik trafia do gałęzi `q2Eyes = True`
(`I2MC.py`, w. 1455–1462), która:

1. uśrednia oba kanały — a średnia dwóch identycznych sygnałów to ten sam sygnał,
2. uruchamia `two_cluster_weighting` osobno dla „lewego" i „prawego" oka, czyli
   dwukrotnie na tych samych danych,
3. uśrednia obie macierze wag (`np.nanmean`, w. 1537).

Odporność na szum wynikająca z niezależnego grupowania dwóch oczu jest tu
niemożliwa do uzyskania, bo niezależnych sygnałów nie ma.

**Pomiar.** Porównano wariant obecny (`dup`) z uczciwie jednoocznym (`mono`,
do I2MC trafia tylko `L_X`/`L_Y`). Gdyby duplikacja cokolwiek wnosiła, wyniki
musiałyby się różnić systematycznie. Nie różnią się:

| efekt | średnia \|zmiana\| wyniku | maksimum |
|---|---|---|
| duplikacja oka lewego (`dup` − `mono`) | **0,0052** | 0,0108 |
| rozrzut losowy samego algorytmu (SD między ziarnami) | 0,0170 | — |

Efekt duplikacji jest **trzykrotnie mniejszy niż własny szum losowy algorytmu**,
czyli nieodróżnialny od zera. Na poziomie cech modelu przesunięcie `mono` − `dup`
nie przekracza 0,054 populacyjnego odchylenia standardowego (mediana ≤ 0,042 SD).

Koszt jest natomiast realny: średni czas segmentacji jednego uczestnika wyniósł
**10,71 s w wariancie `dup` wobec 5,51 s w `mono`** — dokładnie 1,94×. Diagnoza
z opisu problemu jest więc poprawna w obu częściach: obuoczność nie jest
wykorzystywana, a grupowanie wykonuje się dwa razy bez zysku.

---

## 2. Czy przejście na analizę obuoczną zmieni wyniki?

**Tak, i to znacznie bardziej niż wynikałoby z samej „redukcji szumu".**

Kluczowa obserwacja jest taka, że obuoczne I2MC nie polega wyłącznie na
uśrednieniu wag z dwóch grupowań. Zmienia się **sam sygnał, na którym liczone są
pozycje fiksacji**: `get_fixations` dostaje `average_X`/`average_Y`, czyli punkt
cyklopowy (średnią obu oczu), a nie pozycję oka lewego. Rozbieżność między oczami
w badanych plikach jest realna — mediana odległości między punktami obu oczu
wynosi od 19 do 29 px (ok. 0,5–0,8° kąta widzenia), a systematyczne przesunięcie
w pionie sięga 18 px. To nie jest szum do uśrednienia, tylko inny punkt pomiarowy.

### 2.1. Hierarchia efektów

| efekt | średnia \|zmiana\| wyniku | maksimum | krotność szumu RNG |
|---|---|---|---|
| duplikacja oka lewego (`dup` − `mono`) | 0,0052 | 0,0108 | 0,3× |
| **rozrzut losowy k-means (SD)** | **0,0170** | — | 1,0× |
| wybór oka: lewe vs prawe | 0,0437 | 0,0692 | 2,6× |
| **przejście na obuoczne (`bino` − `dup`)** | **0,0425** | **0,1042** | **2,5×** |

Kierunek zmiany przy przejściu na obuoczne jest **systematycznie dodatni:
+0,0405** (wzrost oceny ryzyka u 4 z 5 uczestników).

### 2.2. Wyniki dla poszczególnych uczestników

Średnie z 12 ziaren RNG:

| uczestnik | etykieta | `dup` (obecny) | `mono` | `mono_r` (prawe oko) | `bino` (obuoczny) | `bino` − `dup` |
|---|---|---|---|---|---|---|
| 1075 | non-dyslexic | 0,223 | 0,226 | 0,157 | 0,280 | **+0,057** |
| 1082 | dyslexic | 0,949 | 0,950 | 0,917 | 0,971 | +0,022 |
| 1090 | non-dyslexic | 0,224 | 0,235 | 0,172 | 0,219 | −0,005 |
| 1095 | non-dyslexic | 0,176 | 0,170 | 0,152 | 0,201 | +0,025 |
| 1109 | non-dyslexic | 0,108 | 0,114 | 0,148 | 0,212 | **+0,104** |

U żadnego z tych pięciu uczestników nie dochodzi do zmiany klasyfikacji, ale
wszyscy leżą daleko od progu 0,5 — to nie jest dowód stabilności, tylko brak
testu w strefie granicznej (patrz §2.4).

### 2.3. Przesunięcie cech diagnostycznych

Przesunięcie mierzone w jednostkach populacyjnego odchylenia standardowego
z `model_config.json` — czyli dokładnie w skali, w jakiej model waży cechy:

| cecha | mediana | maksimum | waga β |
|---|---|---|---|
| `fix_prog_duration` | 0,22 SD | **0,79 SD** | +1,041 |
| `sac_prog_y_stab` | 0,40 SD | **0,64 SD** | +0,764 |
| `fix_reg_duration` | 0,15 SD | 0,41 SD | +1,707 |
| `fix_reg_std` | 0,19 SD | 0,22 SD | −0,329 |
| `sac_prog_dist_avg` | 0,15 SD | 0,26 SD | −0,165 |

Przełożenie na logit modelu (suma β·Δz) wynosi od −0,03 do **+0,81** w zależności
od uczestnika. Zmiany nie mają jednego kierunku dla wszystkich cech i wszystkich
osób — np. `sac_prog_y_stab` spada o 13–25% u trzech uczestników, ale rośnie
o 22% u jednego. To znaczy, że **efekt nie da się skompensować przesunięciem
progu ani przeskalowaniem wyniku**.

Zmienia się także liczba wykrywanych fiksacji — spada u 4 z 5 uczestników,
najsilniej u 1082 (294 → 262, czyli −11%) i 1095 (183 → 166, −9,5%). Jest to
spójne z tym, czego należy oczekiwać: uśrednienie oczu wygładza sygnał, więc
próbki łatwiej łączą się w mniejszą liczbę dłuższych fiksacji.

### 2.4. Konsekwencja dla modelu — najważniejszy wniosek

`model_config.json` (tabela `STATS` oraz wagi) został wytrenowany na cechach
policzonych **z oka lewego**. Podanie do niego cech obuocznych to podanie danych
z innego rozkładu. Ponieważ przesunięcia sięgają 0,79 SD, standaryzacja z-score
przestaje być poprawna, a wagi przestają odpowiadać danym.

**Przejście na analizę obuoczną wymaga ponownego przeliczenia całego zbioru
70 uczestników i retreningu modelu (`model_trainer.py`).** Nie da się zmienić
tylko segmentacji i zostawić modelu.

Skala ryzyka, gdyby tego zaniechano — rozkład opublikowanych wyników wokół progu:

- 4 uczestników ma \|score − 0,5\| < 0,05,
- 7 uczestników ma \|score − 0,5\| < 0,10,
- 13 uczestników (19%) leży w przedziale 0,35–0,65.

Systematyczne przesunięcie +0,04 zmieniłoby klasyfikację 1 uczestnika,
przesunięcie +0,10 (obserwowane maksimum) — 4 uczestników. Przy 70 osobach
i wyniku dokładności rzędu kilkudziesięciu procent to zmiana istotna dla
raportowanych metryk.

### 2.5. Czy obuoczność faktycznie daje odporność na szum?

Na tych danych **nie widać jej w rozrzucie wyniku końcowego**. Średnie
odchylenie międzyziarnowe wyniosło: `mono_r` 0,0113, `dup` 0,0169, `mono` 0,0184,
`bino` 0,0213 — wariant obuoczny jest tu nieznacznie **mniej**, a nie bardziej
stabilny.

Nie jest to argument przeciwko obuoczności: mierzony rozrzut pochodzi z losowej
inicjalizacji k-means, a nie z szumu okulografu, a niezależne grupowanie dwóch
oczu z założenia tłumi to drugie, nie pierwsze. Wniosek jest węższy i wart
odnotowania w pracy: **deklarowana odporność na szum nie przekłada się
automatycznie na powtarzalność wyniku końcowego**, bo dominującym źródłem
rozrzutu w tym potoku jest sam algorytm (patrz §3.2).

### 2.6. Wybór oka jest arbitralny i mierzalnie istotny

Wariant `mono_r` (samo oko prawe) różni się od `mono` (samo oko lewe) średnio
o 0,044, maksymalnie o 0,069 — czyli **tak samo silnie jak całe przejście na
obuoczność** i 2,6× powyżej szumu losowego. Milczące wybranie oka lewego jest
zatem nieudokumentowanym stopniem swobody, który realnie wpływa na wynik
pojedynczego uczestnika. To wzmacnia argument za ujawnieniem tej decyzji w §4.4.1.

---

## 3. Ustalenia uboczne (poza zakresem pytania, ale istotne dla pracy)

### 3.1. Kolumna `score` w opublikowanym CSV jest nieaktualna

`wyniki_grupowe_etdd70_meaningful_text.csv` zawiera kolumnę `score` policzoną
**poprzednią** wersją modelu. Przeliczenie wyniku z kolumn cech tego samego pliku
przy użyciu obecnego `model_config.json` daje inne wartości: zgodnych jest
7 z 70 rekordów, średnia różnica +0,033 (maks. +0,10), a **2 uczestników zmienia
klasyfikację**.

Przyczyna jest sekwencyjna: `analysis_group` policzył `score` używając
ówczesnego `model_config.json`, po czym `model_trainer.py` nadpisał ten plik
nowymi wagami wytrenowanymi na tym samym CSV. Kolumny cech są spójne (i to na
nich trenuje się model), ale kolumny `score`/`risk_group` opisują już nieistniejący
model. Dodatkowo plik powstał przed commitem `6ff7082`, który zmienił `maxdisp`
z 99999 na wartość domyślną biblioteki.

Weryfikacja: odtworzenie potoku przy `maxdisp = 99999` **i** przeliczeniu wyniku
aktualnym modelem daje 0,232 / 0,948 / 0,182 / 0,190 / 0,105 wobec oczekiwanych
0,24 / 0,95 / 0,18 / 0,19 / 0,10 — zgodność dla wszystkich pięciu uczestników.
Potwierdza to zarówno przyczynę rozbieżności, jak i wierność odtworzenia potoku
użytego w niniejszej analizie.

*Zalecenie:* przeliczyć zbiór aktualnym kodem i nadpisać CSV przed cytowaniem
z niego wyników w pracy.

### 3.2. Potok jest niedeterministyczny

`I2MC.kmeans2` inicjalizuje centroidy metodą k-means++ używając `np.random.randint`
i `np.random.rand` **bez ustawionego ziarna** (`I2MC.py`, w. 535–547). Każde
uruchomienie tego samego pliku daje inny wynik: zaobserwowany rozstęp wyniku dla
jednego uczestnika sięga 0,13 (uczestnik 1095, wariant `bino`: 0,15–0,28).

Dla pracy dyplomowej oznacza to, że raportowane liczby nie są odtwarzalne przez
recenzenta. Wystarczy `np.random.seed(...)` na początku
`process_single_subject`/`run_analysis` (przy `ProcessPoolExecutor` ziarno trzeba
ustawić wewnątrz procesu roboczego, tak jak robi to `porownanie_obuoczne.py`).

### 3.3. Automatyczne wykrywanie częstotliwości nie działa na ETDD70

Znaczniki czasu w ETDD70 są w **mikrosekundach** (mediana odstępu 4000 = 4 ms =
250 Hz). `estimate_sample_rate_ms` rozpoznaje tylko sekundy i milisekundy, więc
interpretuje 4000 jako ms, wylicza 0,25 Hz, odrzuca jako nierealistyczne i
przechodzi na wartość zapasową `GROUP_EXPERIMENT_FREQ = 250`.

Wynik jest przypadkowo poprawny (zapasowe 250 Hz to rzeczywista częstotliwość
zbioru), ale reklamowana w komentarzu autodetekcja nie jest na tym zbiorze
w ogóle wykonywana. Dla zbioru o innej częstotliwości dałoby to po cichu błędny
wynik. Poprawka to jedna gałąź: `median_diff >= 1000` → mikrosekundy.

---

## 4. Rekomendacja

1. **W obecnej wersji pracy** — ujawnić decyzję w §4.4.1 (tekst w §5 poniżej).
   Analiza potwierdza, że sformułowanie „wykorzystanie niezależnych sygnałów obu
   oczu pozostaje kierunkiem dalszego rozwoju" jest zgodne ze stanem faktycznym.
2. **Nie wprowadzać obuoczności punktowo.** Zmiana jest tania w kodzie (§6), ale
   pociąga za sobą przeliczenie 70 uczestników i retrening modelu. Wprowadzona bez
   retreningu pogorszy wyniki, bo poda modelowi cechy z innego rozkładu.
3. **Jeżeli jest czas na retrening** — zrobić to razem z §3.1 (odświeżenie CSV)
   i §3.2 (ustawienie ziarna), bo bez determinizmu nie da się wykazać, że zmiana
   metryk pochodzi z obuoczności, a nie z losowania. Wtedy porównanie
   „jednooczny vs obuoczny" na pełnych 70 uczestnikach staje się samodzielnym,
   mocnym wynikiem metodologicznym pracy.
4. **Niezależnie od decyzji o obuoczności** — usunąć samą duplikację
   (`'R_X': x_data`), bo w wariancie jednoocznym nie wnosi nic (0,005 wobec
   0,017 szumu), a podwaja czas obliczeń. To zmiana bez wpływu na wyniki,
   zgodna z narracją o optymalizacji z §4.4.5.

---

## 5. Tekst do §4.4.1

> **Obsługa sygnału obuocznego:** Zbiór referencyjny zawiera zapis z obu oczu.
> W bieżącej wersji potoku do segmentacji wykorzystywany jest sygnał oka lewego,
> który przekazywany jest do obu kanałów wejściowych algorytmu; wykorzystanie
> niezależnych sygnałów obu oczu — będące źródłem dodatkowej odporności I2MC na
> szum — pozostaje kierunkiem dalszego rozwoju. Dane z okulografu Gazepoint
> GP3 HD rejestrowane są natomiast jako uśredniony punkt spojrzenia (BPOG), co
> stanowi różnicę metodologiczną między obydwoma potokami i zostało uwzględnione
> przy interpretacji wyników.

Zdanie o BPOG jest zgodne z kodem: `gazepoint.py` włącza `ENABLE_SEND_POG_BEST`
i zapisuje wyłącznie `BPOGX`/`BPOGY`/`BPOGV`, a `analysis_individual.py` (w. 18–19)
czyta właśnie te kolumny. Potok indywidualny operuje więc na punkcie już
uśrednionym przez okulograf — w tym sensie jest bliższy wariantowi `bino` niż
obecnemu wariantowi grupowemu, co uzasadnia nazwanie tego różnicą metodologiczną.

Opcjonalne rozszerzenie, jeśli praca ma podawać wielkość pominiętego efektu:

> Wpływ tej decyzji zmierzono na pięciu uczestnikach zbioru referencyjnego:
> przejście na rzeczywistą analizę obuoczną przesuwa cechy diagnostyczne o maksymalnie
> 0,79 populacyjnego odchylenia standardowego, a wynik modelu średnio o 0,04
> (maksymalnie 0,10), co wymagałoby ponownego wyznaczenia wag modelu.

---

## 6. Gotowa zmiana w kodzie (do zastosowania po decyzji o retreningu)

Zmiana jest odwracalna i mieści się w dwóch plikach.

**`analysis_core.py`** — sekcja „4. Przygotowanie danych wejściowych"
(zastępuje w. 117–132):

```python
    # 4. Przygotowanie danych wejściowych
    time_data = df.index.values * sample_rate_ms

    def _kanal(nazwa):
        wartosci = df[nazwa].values.astype(float)
        return np.where(np.isfinite(wartosci), wartosci, np.nan)

    data = {'time': time_data, 'L_X': _kanal('x'), 'L_Y': _kanal('y')}

    # Kanał prawego oka podawany jest tylko wtedy, gdy źródło rzeczywiście
    # zawiera drugi, niezależny sygnał (ETDD70). Dla Gazepoint GP3 HD zapisywany
    # jest już uśredniony punkt BPOG, więc do I2MC trafia jeden kanał: wpisanie
    # tego samego sygnału po obu stronach nie dodaje informacji, a podwaja czas
    # grupowania (zmierzone: 10,7 s wobec 5,5 s na uczestnika).
    if 'x_prawe' in df.columns and df['x_prawe'].notna().any():
        data['R_X'] = _kanal('x_prawe')
        data['R_Y'] = _kanal('y_prawe')
```

**`analysis_group.py`** — przygotowanie danych w `process_single_subject`
(zastępuje w. 21–23 i 35–36):

```python
        clean_df = pd.DataFrame()
        clean_df['x'] = df['gaze_x_left']
        clean_df['y'] = df['gaze_y_left']
        clean_df['x_prawe'] = df['gaze_x_right']
        clean_df['y_prawe'] = df['gaze_y_right']
```

```python
        # Filtr poprawności stosowany osobno do każdego oka: próbka odrzucona
        # na jednym oku nie unieważnia drugiego, bo I2MC potrafi skorzystać
        # z oka pozostałego (I2MC.average_eyes).
        bledne_lewe = ~((clean_df['x'] > 1) & (clean_df['y'] > 1))
        bledne_prawe = ~((clean_df['x_prawe'] > 1) & (clean_df['y_prawe'] > 1))
        clean_df.loc[bledne_lewe, ['x', 'y']] = np.nan
        clean_df.loc[bledne_prawe, ['x_prawe', 'y_prawe']] = np.nan
```

Po zastosowaniu obu fragmentów konieczna jest kolejność: przeliczenie zbioru
(`analysis_group.run_analysis`) → `model_trainer.py --input <nowy CSV>` →
aktualizacja zestawu awaryjnego w `analysis_core.calculate_risk_score`.

---

## 7. Odtworzenie pomiarów

```bash
python porownanie_obuoczne.py --dane <katalog z Subject_*_raw.csv> --powtorzenia 12
```

Skrypt nie modyfikuje potoku diagnostycznego — buduje słownik wejściowy I2MC
czterema sposobami i przepuszcza wynik przez niezmienione
`analysis_core.classify_movements`, `calculate_features` i `calculate_risk_score`.
Środowisko użyte w analizie: Python 3.11, I2MC 2.2.8.

Ograniczenie: pomiary wykonano na 5 z 70 uczestników (tylko te pliki surowe były
dostępne). Kierunek i skala efektu są spójne między uczestnikami, ale wpływ na
metryki klasyfikacji całego zbioru (dokładność, czułość, swoistość) wymaga
przeliczenia pełnych 70 rekordów.
