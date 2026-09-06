# Analiza wprowadzenia obuocznej segmentacji I2MC

> **Status: zmiana wdrożona.** Oba potoki — eksperymentalny (`gazepoint.py`,
> `analysis_individual.py`) i analityczny (`analysis_core.py`,
> `analysis_group.py`) — pracują obecnie obuocznie. Rozdziały 1–3 opisują stan
> **sprzed** tej zmiany i stanowią jej uzasadnienie; rozdział 4 opisuje, co
> zostało zrobione i co pozostaje do zrobienia (retrening modelu).
> Zakres wdrożenia: §4, zmienione fragmenty kodu: §6.

Dokument odpowiada na dwa pytania: (1) czy postawiona diagnoza — że potok
analizuje jedno oko, a obuoczność I2MC nie jest wykorzystywana — była prawdziwa,
oraz (2) czy przejście na rzeczywistą analizę obuoczną zmieni wyniki końcowe.

Wszystkie liczby pochodzą ze skryptu `porownanie_obuoczne.py` uruchomionego na
pięciu uczestnikach ETDD70 (T4 Meaningful Text: 1075, 1082, 1090, 1095, 1109),
po 12 powtórzeń na wariant, łącznie 240 przebiegów I2MC.

---

## 1. Potwierdzenie diagnozy

Przed zmianą `analysis_core.apply_i2mc_segmentation` budował słownik wejściowy,
w którym `L_X`/`L_Y` i `R_X`/`R_Y` wskazywały na **tę samą tablicę** — sygnał oka
lewego pobrany w `analysis_group.process_single_subject` z kolumn `gaze_x_left`
i `gaze_y_left`. Kolumny `gaze_x_right`/`gaze_y_right` nie były wczytywane w ogóle.

W bibliotece I2MC (wersja 2.2.8) taki słownik trafia do gałęzi `q2Eyes = True`
(`I2MC.py`, w. 1455–1462), która:

1. uśrednia oba kanały — a średnia dwóch identycznych sygnałów to ten sam sygnał,
2. uruchamia `two_cluster_weighting` osobno dla „lewego" i „prawego" oka, czyli
   dwukrotnie na tych samych danych,
3. uśrednia obie macierze wag (`np.nanmean`, w. 1537).

Odporność na szum wynikająca z niezależnego grupowania dwóch oczu jest tu
niemożliwa do uzyskania, bo niezależnych sygnałów nie ma.

**Pomiar.** Porównano wariant sprzed zmiany (`dup`) z uczciwie jednoocznym (`mono`,
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

| uczestnik | etykieta | `dup` (przed zmianą) | `mono` | `mono_r` (prawe oko) | `bino` (obuoczny) | `bino` − `dup` |
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

### 3.2. Niedeterminizm potoku — rozwiązany

`I2MC.kmeans2` inicjalizuje centroidy metodą k-means++ używając `np.random.randint`
i `np.random.rand` **bez ustawionego ziarna** (`I2MC.py`, w. 535–547). Przed
zmianą każde uruchomienie tego samego pliku dawało inny wynik: zaobserwowany
rozstęp oceny ryzyka dla jednego uczestnika sięgał 0,13 (uczestnik 1095, wariant
`bino`: 0,15–0,28), czyli **więcej niż różnica między analizą jednooczną
a obuoczną**. Raportowanych liczb nie dałoby się odtworzyć ani porównać między
wersjami potoku.

**Rozwiązanie.** `analysis_core.run_i2mc` ustawia ziarno
(`I2MC_RANDOM_SEED = 42`) bezpośrednio przed wywołaniem I2MC i przywraca
poprzedni stan generatora po zakończeniu. Ziarno ustawiane jest wewnątrz samej
segmentacji, więc obejmuje wszystkie potoki i nie da się go pominąć; przywracanie
stanu sprawia, że funkcja nie zmienia po cichu losowości w kodzie wywołującym —
istotne przy analizie grupowej, gdzie jeden proces roboczy przetwarza wielu
uczestników po kolei. `I2MC_RANDOM_SEED = None` przywraca zachowanie losowe,
gdyby trzeba było zmierzyć rozrzut przez produkcyjny potok.

Zweryfikowane: trzy kolejne przebiegi analizy grupowej dają bajtowo identyczny
plik wyników, a uczestnik policzony osobno daje ten sam wynik co policzony
w grupie (kolejność kończenia procesów roboczych nie ma znaczenia).

**Czego to nie załatwia.** Ustalone ziarno zamraża jedno konkretne losowanie,
nie usuwa rozrzutu. Porównanie wyniku przy ziarnie 42 z rozkładem z 12 ziaren
(wariant `bino`) pokazuje, gdzie to losowanie wypadło:

| uczestnik | ziarno 42 | mediana | min–max | percentyl |
|---|---|---|---|---|
| 1075 | 0,25 | 0,27 | 0,25–0,33 | 25% |
| 1082 | 0,97 | 0,97 | 0,96–0,98 | 46% |
| 1090 | 0,26 | 0,21 | 0,20–0,27 | 92% |
| 1095 | 0,30 | 0,19 | 0,15–0,28 | 100% |
| 1109 | 0,21 | 0,21 | 0,21–0,22 | 38% |

Dla uczestnika 1095 ziarno 42 daje wynik powyżej maksimum z 12 wcześniejszych
losowań. Przy 12 próbkach wypadnięcie nowego losowania poza zaobserwowany zakres
zdarza się z prawdopodobieństwem ok. 15% na uczestnika, więc jeden taki przypadek
na pięciu jest oczekiwany — ale pokazuje, że **wynik pojedynczego uczestnika
przy ustalonym ziarnie nie jest „tym właściwym", tylko jednym z rozkładu**.
Ziarno 42 wybrano arbitralnie, przed obejrzeniem wyników; dobieranie go pod
wynik byłoby zwykłym przeszukiwaniem ziaren.

Wniosek dla pracy: liczby raportować z ustalonym ziarnem (są odtwarzalne),
a wielkość rozrzutu podać osobno, uruchamiając `porownanie_obuoczne.py` na
kilkunastu ziarnach. Rozrzut jest własnością algorytmu, nie błędem pomiaru.

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

## 4. Stan wdrożenia i dalsze kroki

Zmiana została wprowadzona w obu potokach (szczegóły w §6). Pozostaje retrening.

**Zrobione:**

1. **Potok eksperymentu** — `gazepoint.py` włącza `ENABLE_SEND_POG_LEFT`
   i `ENABLE_SEND_POG_RIGHT` i zapisuje kolumny `LPOGX/LPOGY/LPOGV` oraz
   `RPOGX/RPOGY/RPOGV`. Wcześniej rejestrowany był wyłącznie uśredniony przez
   okulograf punkt `BPOG`, więc nawet po zmianie samej analizy nie byłoby z czego
   odtworzyć dwóch niezależnych sygnałów. `BPOG` zostaje — służy do podglądu na
   żywo i jako zapas.
2. **Potok analizy** — `analysis_core.apply_i2mc_segmentation` podaje do I2MC
   kanał prawego oka tylko wtedy, gdy źródło rzeczywiście zawiera drugi zapis;
   `analysis_group` czyta `gaze_x_right`/`gaze_y_right` z ETDD70,
   `analysis_individual` czyta `LPOG*`/`RPOG*` z nagrań GP3.
3. **Filtr poprawności działa osobno na każdym oku** — próbka odrzucona na jednym
   oku nie unieważnia drugiego (I2MC potrafi skorzystać z oka pozostałego).
   W potoku indywidualnym uwzględniana jest przy tym flaga `POGV` z okulografu:
   GP3 przy zgubionym oku podaje ostatnią znaną pozycję, która mieści się
   w zakresie 0–1 i przeszłaby przez sam test zakresu.
4. **Usunięta duplikacja** — w trybie jednoocznym (stare nagrania na `BPOG`,
   pliki bez kolumn prawego oka) do I2MC trafia jeden kanał zamiast tego samego
   sygnału wpisanego dwa razy. Nie zmienia to wyników (0,005 wobec 0,017 szumu),
   a skraca segmentację o połowę — zgodnie z narracją o optymalizacji z §4.4.5.
5. **Ustalone ziarno generatora losowego** — `analysis_core.run_i2mc` seeduje
   I2MC (`I2MC_RANDOM_SEED = 42`), więc potok jest odtwarzalny; szczegóły
   i zastrzeżenia w §3.2. Bez tego nie dałoby się wykazać, że zmiana metryk po
   retreningu pochodzi z obuoczności, a nie z losowej inicjalizacji k-means.
6. **Zgodność wstecz** — nagrania i pliki bez drugiego oka nadal działają,
   schodząc do trybu jednoocznego z komunikatem w konsoli. Oko bez ani jednej
   poprawnej próbki jest odrzucane, zamiast trafiać do I2MC jako kolumna samych
   NaN (grupowanie takiego kanału przewróciłoby segmentację także dla oka
   sprawnego).

**Do zrobienia:**

7. **Retrening modelu** — konieczny, nie opcjonalny. `model_config.json` zawiera
   wagi i tabelę `STATS` wyznaczone na cechach jednoocznych; cechy obuoczne
   pochodzą z innego rozkładu (przesunięcia do 0,79 SD, §2.3), więc dopóki model
   nie zostanie przetrenowany, wyniki są policzone niespójnym modelem.
   Kolejność: `analysis_group.run_analysis` na pełnym zbiorze →
   `model_trainer.py --input <nowy CSV>` → przepisanie nowych wag do zestawu
   awaryjnego w `analysis_core.calculate_risk_score`.
8. **Zaktualizować §4.4.1 pracy** — akapit opisujący analizę jednooczną jest już
   nieaktualny. Gotowy tekst po zmianie: §5 (wersja archiwalna: §5.1).

---

## 5. Tekst do §4.4.1

Wersja **po wdrożeniu obuoczności** — do wstawienia w pracy:

> **Obsługa sygnału obuocznego:** Zarówno zbiór referencyjny, jak i nagrania
> z własnego stanowiska zawierają zapis z obu oczu, i oba sygnały są
> wykorzystywane w segmentacji. Algorytm I2MC grupuje każde oko niezależnie,
> a następnie uśrednia wagi grupowania — stąd bierze się jego odporność na szum
> pomiarowy, ponieważ artefakt obecny w zapisie jednego oka nie ma
> odpowiednika w drugim. Pozycje fiksacji wyznaczane są z punktu uśrednionego
> z obu oczu. Próbka odrzucona jako niepoprawna na jednym oku nie unieważnia
> drugiego: jeżeli w danym momencie widoczne jest tylko jedno oko, analiza
> korzysta z sygnału dostępnego, a do trybu jednoocznego schodzi dopiero wtedy,
> gdy drugie oko nie zawiera ani jednej poprawnej próbki. W przypadku okulografu
> Gazepoint GP3 HD wymagało to włączenia przesyłania punktu spojrzenia osobno dla
> każdego oka (LPOG, RPOG); rejestrowany równolegle uśredniony punkt spojrzenia
> (BPOG) zachowano na potrzeby podglądu na żywo oraz jako zapas dla nagrań,
> w których któreś z oczu nie było widoczne.

Opcjonalne rozszerzenie, jeśli praca ma podawać wielkość efektu tej decyzji:

> Wpływ przejścia z analizy jednoocznej na obuoczną zmierzono na pięciu
> uczestnikach zbioru referencyjnego: cechy diagnostyczne przesuwają się
> o maksymalnie 0,79 populacyjnego odchylenia standardowego, a wynik modelu
> średnio o 0,04 (maksymalnie 0,10). Z tego powodu wagi modelu wyznaczono
> ponownie na cechach policzonych w trybie obuocznym.

*(Ostatnie zdanie dopisać dopiero po faktycznym retreningu — patrz §4, punkt 6.)*

---

### 5.1. Wersja archiwalna (sprzed zmiany)

Akapit opisujący stan jednooczny, gdyby praca miała dokumentować wersję potoku
sprzed wdrożenia:

> **Obsługa sygnału obuocznego:** Zbiór referencyjny zawiera zapis z obu oczu.
> W bieżącej wersji potoku do segmentacji wykorzystywany jest sygnał oka lewego,
> który przekazywany jest do obu kanałów wejściowych algorytmu; wykorzystanie
> niezależnych sygnałów obu oczu — będące źródłem dodatkowej odporności I2MC na
> szum — pozostaje kierunkiem dalszego rozwoju. Dane z okulografu Gazepoint
> GP3 HD rejestrowane są natomiast jako uśredniony punkt spojrzenia (BPOG), co
> stanowi różnicę metodologiczną między obydwoma potokami i zostało uwzględnione
> przy interpretacji wyników.

Zdanie o BPOG było zgodne z ówczesnym kodem: `gazepoint.py` włączał wyłącznie
`ENABLE_SEND_POG_BEST` i zapisywał tylko `BPOGX`/`BPOGY`/`BPOGV`, a
`analysis_individual.py` czytał właśnie te kolumny. Po zmianie różnica
metodologiczna między potokami zniknęła — oba pracują na dwóch niezależnych
sygnałach.

---

## 6. Wdrożona zmiana w kodzie

Sedno zmiany to kontrakt na kolumny wejściowe segmentacji. `apply_i2mc_segmentation`
oczekuje w `DataFrame`:

| kolumna | znaczenie | wymagana |
|---|---|---|
| `x`, `y` | oko lewe (albo jedyny dostępny sygnał) | tak |
| `x_prawe`, `y_prawe` | oko prawe | nie |

Kanał prawego oka trafia do I2MC (`R_X`/`R_Y`) **tylko wtedy**, gdy te kolumny
istnieją i zawierają choć jedną poprawną próbkę. W przeciwnym razie do algorytmu
idzie jeden kanał — bez wpisywania tego samego sygnału po obu stronach, co
wcześniej podwajało czas grupowania bez żadnego zysku. Tryb, w którym pracuje
segmentacja, jest wypisywany w konsoli (`obuocznie` / `jednoocznie`), a w potoku
indywidualnym trafia też do raportu tekstowego jako „Tryb segmentacji".

Kto wypełnia te kolumny:

- `analysis_group.process_single_subject` — z `gaze_x_left`/`gaze_y_left`
  i `gaze_x_right`/`gaze_y_right` zbioru ETDD70,
- `analysis_individual.run_analysis` — z `LPOGX`/`LPOGY` i `RPOGX`/`RPOGY`
  nagrania GP3, a dla nagrań sprzed zmiany w `gazepoint.py` z uśrednionego
  `BPOGX`/`BPOGY` (wtedy tryb jednooczny),
- `gazepoint.py` — zapisuje `LPOG*`/`RPOG*` dzięki komendom
  `ENABLE_SEND_POG_LEFT` i `ENABLE_SEND_POG_RIGHT`; bez nich GP3 wysyła sam
  `BPOG` i drugiego sygnału nie da się odtworzyć na etapie analizy.

Dokładny diff: `git show` na commicie wprowadzającym obuoczność.

Kolejność dalszych kroków: przeliczenie zbioru (`analysis_group.run_analysis`) →
`model_trainer.py --input <nowy CSV>` → przepisanie nowych wag do zestawu
awaryjnego w `analysis_core.calculate_risk_score`.

---

## 7. Odtworzenie pomiarów

```bash
python porownanie_obuoczne.py --dane <katalog z Subject_*_raw.csv> --powtorzenia 12
```

Skrypt nie modyfikuje potoku diagnostycznego — buduje słownik wejściowy I2MC
czterema sposobami i przepuszcza wynik przez niezmienione
`analysis_core.classify_movements`, `calculate_features` i `calculate_risk_score`.
Ziarnem steruje samodzielnie (jedno ziarno na numer powtórzenia, wspólne dla
wszystkich wariantów), z pominięciem stałego `I2MC_RANDOM_SEED` z potoku
produkcyjnego — inaczej wszystkie powtórzenia dałyby ten sam wynik i rozrzutu
nie dałoby się zmierzyć. To jest właśnie narzędzie, którym podaje się w pracy
wielkość rozrzutu obok liczb z ustalonym ziarnem (§3.2).
Środowisko użyte w analizie: Python 3.11, I2MC 2.2.8.

Ograniczenie: pomiary wykonano na 5 z 70 uczestników (tylko te pliki surowe były
dostępne). Kierunek i skala efektu są spójne między uczestnikami, ale wpływ na
metryki klasyfikacji całego zbioru (dokładność, czułość, swoistość) wymaga
przeliczenia pełnych 70 rekordów.
