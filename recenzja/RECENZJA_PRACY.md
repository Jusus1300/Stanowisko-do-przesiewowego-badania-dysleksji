# Recenzja pracy dyplomowej

**Tytuł:** *Stworzenie stanowiska do przesiewowego badania dysleksji na podstawie badań okulografem*
**Zakres recenzji:** spójność logiczna, precyzja cytowania, zgodność dokumentacji z kodem, ryzyka implementacyjne
**Materiał:** `main.pdf` (55 stron) + repozytorium `Jusus1300/Stanowisko-do-przesiewowego-badania-dysleksji` @ `1e8ecad`
**Data:** 2026-09-06

> **Metoda.** Wszystkie ustalenia liczbowe zostały odtworzone obliczeniowo. Zbiór wyników
> `wyniki_grupowe_etdd70_meaningful_text.csv` (70 uczestników, etykiety ETDD70) odzyskano
> z historii git (commit `bd60e47`, usunięty w `859dafc`) i przepuszczono przez oryginalny
> `model_trainer.py`. Domyślne parametry biblioteki I2MC 2.2.8 sprawdzono w źródle pakietu.
> Wszędzie tam, gdzie źródła nie dało się pobrać (blokada sieci), fakt oznaczono jako
> *do weryfikacji przez autora* zamiast go rozstrzygać.

---

## 1. Streszczenie problemów

Praca jest **dojrzała metodologicznie i wyjątkowo uczciwa w rozdziałach 5–6** — ograniczenia
(brak walidacji zewnętrznej, podatność na symulację, PPV przy niskiej chorobowości, transfer
językowy) są nazwane wprost i poprawnie. Repozytorium ma bardzo dobry `README.md`, który sam
z siebie dokumentuje część rozbieżności wskazanych niżej. To jest mocna strona całości.

Problemy koncentrują się w **trzech obszarach**, w kolejności wagi:

**A. Wyniki w rozdziale 5 nie odtwarzają się z materiału źródłowego.**
Tabela 5.1 (28/7/7/28) i trzy wartości 80,0% nie wychodzą z żadnego artefaktu w repozytorium.
Uruchomienie `model_trainer.py` na jedynym zachowanym zbiorze cech z etykietami daje
**dokładność 75,7%, czułość 73,7%, swoistość 77,7%**. To jest problem krytyczny: wynik
deklarowany w streszczeniu, w rozdziale 5 i we wnioskach nie ma pokrycia w kodzie i danych.

**B. Rozdział 4 dokumentuje trzy różne wersje systemu naraz.**
Równanie (3.2) pochodzi z commita `bd60e47`, repozytorium zawiera nowszy model (`8b730cd`)
z innymi wagami, a Rys. 4.19 pokazuje raport z wersji **sprzed pierwszego commita** — z cechami
w pikselach i wynikiem modelu `0.000`, który jest artefaktem niezgodności jednostek.
Rys. 4.1 przedstawia jako „Zadanie 1: Czytanie tekstu" ekran odprawy misji o długości sześciu
wierszy, przy 28 wykrytych fiksacjach.

**C. Interpretacja merytoryczna dwóch z pięciu cech modelu jest sprzeczna z danymi.**
Cecha `fix_reg_std` (x3) jest w zbiorze ETDD70 **wyższa** u dyslektyków (d = +1,25; AUC = 0,867 —
najsilniejszy pojedynczy dyskryminator), a praca w §3.4.4 interpretuje jej ujemny współczynnik
jako dowód „nadmiernej monotonii" fiksacji powrotnych. To odwrócenie kierunku efektu: ujemny
znak jest artefaktem kolinearności (r = 0,86 z x1), a nie zjawiskiem poznawczym.

Do tego dochodzi warstwa drobniejsza: rozbieżności nazw plików między Rys. 3.5 a kodem,
niepełny opis rejestrowanych kanałów w §4.2.1, angielska wersja streszczenia bez zastrzeżeń
obecnych w wersji polskiej, oraz kilkanaście usterek edytorskich i bibliograficznych.

**Ocena syntetyczna:** praca inżynierska o dobrej wartości technicznej, z rzetelną dyskusją
ograniczeń, ale wymagająca **obowiązkowej korekty rozdziałów 4–5** przed obroną. Poprawki
krytyczne (rozdz. 2 niniejszej recenzji) są w większości redakcyjne i możliwe do wykonania
bez powtarzania badań — z jednym wyjątkiem: liczby w tabeli 5.1 trzeba przeliczyć od nowa.

---

## 2. Poprawki krytyczne

Sześć pozycji, bez których praca zawiera twierdzenia nieprawdziwe lub nieweryfikowalne.

### K1. Tabela 5.1 i wartości 80,0% nie mają pokrycia w danych

**Gdzie:** s. 1 (Streszczenie), s. 2 (Abstract), s. 47 (§5.1.1, Tab. 5.1), s. 49 (§5.3), s. 52 (§6.2).

**Stan faktyczny.** Odtworzenie procedury opisanej w §3.4.4 i §5.1 (`RepeatedStratifiedKFold`,
7 podziałów × 5 powtórzeń, ziarno 42) na zbiorze `wyniki_grupowe_etdd70_meaningful_text.csv`:

| Wielkość | Praca | Odtworzone |
|---|---|---|
| Dokładność | 80,0% | **75,7% ± 12,9%** |
| Czułość | 80,0% | **73,7% ± 22,3%** |
| Swoistość | 80,0% | **77,7% ± 21,3%** |

Sprawdzono także warianty alternatywne — żaden nie daje 28/7/7/28:

| Wariant | TP | FN | FP | TN | Czułość | Swoistość |
|---|---|---|---|---|---|---|
| Predykcje out-of-fold, `StratifiedKFold(7)`, bez mieszania | 26 | 9 | 8 | 27 | 74,3% | 77,1% |
| Model z równania (3.2), resubstytucja | 27 | 8 | 7 | 28 | 77,1% | 80,0% |
| Model z `model_config.json` (HEAD), resubstytucja | 27 | 8 | 6 | 29 | 77,1% | 82,9% |
| Kolumna `score` w zachowanym CSV | 26 | 9 | 6 | 29 | 74,3% | 82,9% |
| **Praca, Tab. 5.1** | **28** | **7** | **7** | **28** | **80,0%** | **80,0%** |

**Problem drugiego rzędu.** Nawet gdyby liczby się zgadzały, tabela 5.1 jest niewłaściwym
obiektem dla opisanej procedury. Powtarzany sprawdzian krzyżowy z 5 powtórzeniami daje
**35 macierzy pomyłek**, a każdy uczestnik jest klasyfikowany 5 razy. Nie istnieje jedna
macierz 70 przypadków odpowiadająca średniej z foldów — tabela 5.1 jest rekonstrukcją wsteczną
z zaokrąglonej wartości 80%. Dodatkowo `model_trainer.py` w ogóle nie liczy macierzy pomyłek,
więc tabela nie ma źródła w kodzie.

**Co zrobić (jedna z dwóch dróg):**

1. *Droga rzetelna.* Przeliczyć wyniki i zastąpić Tab. 5.1 zestawieniem właściwym dla CV:
   średnia ± odchylenie dla dokładności/czułości/swoistości ze wszystkich 35 foldów, plus
   — jeśli macierz jest potrzebna — osobna macierz z `cross_val_predict` na pojedynczym
   podziale, jawnie tak opisana. Do `model_trainer.py` dopisać wyliczanie macierzy, żeby
   liczby w pracy miały źródło w kodzie.
2. *Droga minimalna.* Jeżeli 80/80/80 pochodzi z wcześniejszego stanu potoku, trzeba wskazać
   który to stan i **dołączyć plik cech, z którego te liczby powstały** — inaczej wynik
   pozostaje nieodtwarzalny.

Wartości 80,0% występują w pracy w pięciu miejscach (streszczenie PL, Abstract, §5.1.1, §5.3,
§6.2) — poprawkę trzeba przeprowadzić wszędzie.

---

### K2. Równanie (3.2) opisuje model, którego nie ma w repozytorium

**Gdzie:** s. 28 (§3.4.4, wzór 3.2), s. 28–29 (interpretacja x1–x5).

Praca podaje:

> Z = 0,272 + 1,707·x₁ + 1,041·x₂ − 0,329·x₃ + 0,764·x₄ − 0,165·x₅

Repozytorium (`model_config.json` oraz zestaw awaryjny w `analysis_core.py`, obie zsynchronizowane):

> Z = 0,295 + 1,509·x₁ + 1,162·x₂ − 0,115·x₃ + 0,720·x₄ − 0,139·x₅

Historia git wyjaśnia rozbieżność jednoznacznie:

| Commit | intercept | β₁ | β₂ | β₃ | β₄ | β₅ | Uwaga |
|---|---|---|---|---|---|---|---|
| `ad66f15` | 0,322 | 1,888 | 0,879 | −0,262 | 0,879 | −0,163 | pierwszy commit |
| `bd60e47` | **0,272** | **1,707** | **1,041** | **−0,329** | **0,764** | **−0,165** | **= równanie (3.2)** |
| `8b730cd` | 0,295 | 1,509 | 1,162 | −0,115 | 0,720 | −0,139 | **stan HEAD** |

Praca opisuje więc model **o jedno przetrenowanie starszy** niż wersja oddana w repozytorium.
Uruchomienie `model_trainer.py --input <odzyskany CSV>` odtwarza dokładnie współczynniki
`bd60e47` — równanie (3.2) jest zatem prawdziwe, tylko nieaktualne.

**Dodatkowo:** commit `8b730cd` („Przetrenowano model na danych z etykietami is_dyslexic")
nie daje się odtworzyć — plik wejściowy dla tego przetrenowania nigdy nie trafił do repozytorium.
Jedyny zachowany CSV pochodzi z `bd60e47` i produkuje wagi `bd60e47`, nie `8b730cd`.

**Co zrobić:** zdecydować, która wersja jest wersją pracy, i doprowadzić do zgodności
równanie (3.2), `model_config.json`, zestaw awaryjny w `analysis_core.py` oraz §9.3 README.
Plik cech z etykietami użyty do finalnego treningu **musi znaleźć się w repozytorium** —
bez niego rozdział 5 jest nieodtwarzalny z definicji.

---

### K3. Rys. 4.19 pokazuje raport z wynikiem będącym artefaktem jednostek

**Gdzie:** s. 46 (Rys. 4.19).

Zrzut ekranu przedstawiony jako „wygenerowany raport końcowy" zawiera:

```
4. Śr. dystans sakad PROG: 294.19 px
5. Max zakres sakad PROG:  573.79 px
6. Stab. Y (Sakady PROG):  15.17 px
...
WYNIK MODELU: 0.000 (Próg: 0.5)
KLASYFIKACJA: Niskie ryzyko
```

Wartości 294,19 i 15,17 są w **pikselach**. Tymczasem tabela populacyjna `STATS` przechowuje
te cechy w **stopniach kąta widzenia** (`sac_prog_dist_avg`: μ = 1,73; `sac_prog_y_stab`: μ = 0,37)
— i tak jest we wszystkich trzech wersjach `model_config.json` w historii repozytorium.
Standaryzacja daje wtedy:

| | z-score x₄ | z-score x₅ | Z | P |
|---|---|---|---|---|
| wagi `ad66f15` | +107,3 | +675,5 | −19,6 | 3,1·10⁻⁹ |
| wagi `bd60e47` (= wzór 3.2) | +123,7 | +685,4 | −22,0 | 2,7·10⁻¹⁰ |
| wagi `8b730cd` (HEAD) | +121,3 | +684,3 | −11,2 | 1,4·10⁻⁵ |

Każdy z tych wyników wyświetla się jako `0.000`. **Klasyfikacja „Niskie ryzyko" na Rys. 4.19
nie jest oceną ryzyka — jest skutkiem podstawienia cech pikselowych do modelu skalibrowanego
w stopniach.** Rysunek dokumentuje stan kodu sprzed pierwszego commita (obecny `analysis_individual.py`
drukuje przy poz. 6 jednostkę `deg`, a nie `px`, i dodatkowo wypisuje wiersz „Tryb segmentacji",
którego na zrzucie nie ma).

**Co zrobić:** wygenerować raport ponownie aktualną wersją kodu i podmienić rysunek. Przy okazji
poprawić dwie usterki w samym raporcie (patrz Z3, Z4).

---

### K4. Interpretacja cechy x₃ jest odwrotna do kierunku efektu w danych

**Gdzie:** s. 28 (§3.4.4, opis x₃).

Praca pisze:

> x₃ – odchylenie standardowe czasu trwania fiksacji regresywnych (`fix_reg_std`); ujemny
> współczynnik (-0,33) w modelu wielowymiarowym sugeruje, że **mniejsza plastyczność
> i nadmierna monotonia (sztywność czasowa) fiksacji powrotnych koreluje z wyższym ryzykiem**
> zaburzenia

Statystyka jednowymiarowa na tym samym zbiorze mówi coś przeciwnego:

| Cecha | Kontrola | Dyslektycy | Kierunek | Cohen d | p (t) | AUC |
|---|---|---|---|---|---|---|
| `fix_reg_duration` (x₁) | 296,4 ms | 378,9 ms | wyższe u dys. | +1,32 | <0,0001 | 0,827 |
| `fix_prog_duration` (x₂) | 362,8 ms | 483,4 ms | wyższe u dys. | +1,34 | <0,0001 | 0,845 |
| **`fix_reg_std` (x₃)** | **205,9 ms** | **330,6 ms** | **wyższe u dys.** | **+1,25** | **<0,0001** | **0,867** |
| `sac_prog_y_stab` (x₄) | 0,347° | 0,388° | wyższe u dys. | +0,34 | 0,158 | 0,578 |
| `sac_prog_dist_avg` (x₅) | 1,909° | 1,564° | niższe u dys. | −0,87 | 0,0005 | 0,268 |

Zmienność czasów fiksacji regresywnych jest u dyslektyków **o 61% większa**, a nie mniejsza —
i jest to zarazem **najsilniejszy pojedynczy dyskryminator w całym zestawie** (AUC = 0,867).
Ujemny współczynnik w modelu wielowymiarowym wynika z kolinearności: r(x₁, x₃) = 0,86.
To klasyczny efekt supresora, a nie zjawisko poznawcze.

Potwierdza to niestabilność współczynnika między foldami:

| Cecha | średnia β | odch. std. β | min | max | znak dodatni |
|---|---|---|---|---|---|
| `fix_reg_duration` | 1,707 | 0,605 | 0,166 | 2,964 | 100% foldów |
| `fix_prog_duration` | 1,041 | 0,337 | 0,537 | 2,232 | 100% foldów |
| **`fix_reg_std`** | **−0,329** | **0,892** | **−1,441** | **+2,340** | **17% foldów** |
| `sac_prog_y_stab` | 0,764 | 0,218 | 0,147 | 1,245 | 100% foldów |
| **`sac_prog_dist_avg`** | **−0,165** | **0,230** | **−0,632** | **+0,307** | **20% foldów** |

Dla x₃ odchylenie standardowe jest **2,7× większe od wartości bezwzględnej średniej**, a znak
zmienia się między foldami. Współczynnik nie jest odróżnialny od zera. To samo dotyczy x₅
(std 0,230 przy średniej −0,165). Rozjazd między trzema wersjami modelu w historii repozytorium
(β₃ = −0,262 / −0,329 / −0,115, czyli rozstęp 0,214 przy średniej 0,235) jest tego samego rzędu.

**Co zrobić:**
- Usunąć merytoryczną interpretację znaku x₃ albo zastąpić ją opisem zgodnym z danymi:
  cecha ma silny **dodatni** efekt jednowymiarowy, a ujemny współczynnik w modelu jest skutkiem
  współliniowości z x₁; sam znak nie niesie treści poznawczej.
- Interpretację x₅ osłabić do „kierunek zgodny z [11], ale współczynnik nieodróżnialny od zera
  przy tej liczebności".
- Dopisać do §5.3 akapit o kolinearności (macierz korelacji + rozrzut wag między foldami).
  To wzmacnia pracę, a nie osłabia: pokazuje, że autor rozumie własny model.
- Rozważyć wzmiankę, że przy r = 0,86 sensowniejszy byłby model regularyzowany (obecnie
  `LogisticRegression(C=np.inf)` — regularyzacja jest **celowo wyłączona**, co przy tej
  kolinearności jest głównym źródłem niestabilności wag).

---

### K5. Streszczenie polskie i angielskie stawiają różne tezy

**Gdzie:** s. 1 vs s. 2.

Streszczenie polskie zawiera trzy istotne zastrzeżenia, których **nie ma w Abstract**:

| Twierdzenie | Streszczenie (PL) | Abstract (EN) |
|---|---|---|
| Walidacja na ETDD70, nie na zbudowanym stanowisku | „**a nie na danych zebranych na zbudowanym stanowisku**" | brak |
| Wyniki charakteryzują model, nie stanowisko | „Uzyskane wyniki charakteryzują zatem **sam model analityczny**" | „Calibration and validation of the analytical system conducted on a group of 70 children **showed that the platform has great potential**" |
| Podatność na symulację objawów | „**wszystkie pięć cech modelu podlega świadomej kontroli badanego**" | brak |
| Wydźwięk zakończenia | „wymaga walidacji na większej grupie, przebadania grupy docelowej…" | „the proposed solution **sets the right direction**" |

Wersja angielska przypisuje wynik „platformie", podczas gdy wersja polska tę atrybucję
wprost prostuje. Recenzent czytający tylko Abstract otrzyma tezę, którą praca sama obala
w §6.2.

**Co zrobić:** przetłumaczyć aktualną wersję polską 1:1. Abstract to nie jest miejsce
na łagodniejszą wersję wniosków.

---

### K6. §5.3.1 przypisuje ograniczenie niewłaściwemu urządzeniu

**Gdzie:** s. 49 (§5.3.1, trzeci punkt).

> **Brak cech szybkich ruchów oka:** Ze względu na częstotliwość próbkowania okulografu
> (150 Hz), model nie uwzględnia cech takich jak maksymalna prędkość sakad.

Dwa błędy w jednym zdaniu:

1. Analizowane przypadki fałszywie ujemne pochodzą ze zbioru **ETDD70, zarejestrowanego
   przy 250 Hz** (praca sama to podaje w §5.1 i w streszczeniu). Częstotliwość Gazepointa
   150 Hz nie ma z nimi nic wspólnego.
2. Rzeczywisty powód braku prędkości szczytowej sakad jest inny i praca zna go dobrze —
   §3.4.2 i §4.4.2 wyjaśniają, że sakady są **rekonstruowane jako wektory między środkami
   sąsiednich fiksacji**, z `duration_samples = 0`. Nie mają własnego czasu trwania, więc
   prędkości nie da się policzyć **przy żadnej częstotliwości próbkowania**.

**Co zrobić:** przepisać punkt tak, by wskazywał na sposób rekonstrukcji zdarzeń (spójnie
z §3.4.2), a nie na sprzęt; jeśli chodzi o częstotliwość, odnieść ją do 250 Hz zbioru ETDD70.

---

## 3. Raport poprawek

Lista wykonawcza. Kolumna „Priorytet": **K** = blokujące, **W** = ważne, **D** = drobne.

### 3.1 Rozdział 5 i wnioski

| # | Priorytet | Lokalizacja | Poprawka |
|---|---|---|---|
| 1 | **K** | s. 47, Tab. 5.1 | Przeliczyć albo zastąpić zestawieniem właściwym dla CV (średnia ± odch. std z 35 foldów) — zob. K1 |
| 2 | **K** | s. 1, 2, 47, 48, 49, 52 | Ujednolicić wartość czułości/swoistości/dokładności we wszystkich pięciu miejscach |
| 3 | **K** | s. 49, §5.3.1 | Poprawić atrybucję braku prędkości sakad (zob. K6) |
| 4 | W | s. 47, §5.1 | Dopisać porównanie z wynikiem autorów ETDD70 (~90% dokładności na tym samym zbiorze) — brak tego odniesienia jest luką w dyskusji |
| 5 | W | s. 48, §5.2.2 | Przeformułować „żaden z uczestników nie został prawidłowo zakwalifikowany do grupy niskiego ryzyka" — zdanie jest niejednoznaczne. Proponowane: „wszyscy uczestnicy symulujący objawy zostali zaklasyfikowani do grupy wysokiego ryzyka (P od 0,71 do 0,95), przy wynikach kontrolnych 0,06–0,32" |
| 6 | W | s. 48, §5.2 | Dopisać, że testy odpornościowe wykonano na stanowisku 1920×1080 przy normach populacyjnych wyznaczonych dla geometrii 1680×1050 / 47,4 cm / 60 cm — wartości P w Tab. 5.2 są obarczone tym przesunięciem (zob. R2) |
| 7 | W | s. 49, §5.3.4 | „Swoboda ruchów u dzieci wprowadza znaczny szum pomiarowy, co zauważono już na etapie wstępnej analizy danych" — żadne dziecko nie było badane na zbudowanym stanowisku; doprecyzować, że obserwacja dotyczy ETDD70 |
| 8 | W | s. 51, §6.1 | „pozwoliło na uzyskanie **stabilnej** rejestracji danych" — twierdzenie nie jest poparte żadną miarą (brak odsetka utraconych próbek, RMS, liczby fiksacji). Albo podać liczby, albo osłabić do „pozwoliło na rejestrację danych" |
| 9 | D | s. 52, §6.2 | „większość wskazań pozytywnych **stanowiłyby** wyniki fałszywie dodatnie" → „stanowiłaby". Sama teza jest poprawna: przy chorobowości 10%, czułości i swoistości 80% wartość predykcyjna dodatnia wynosi 30,8%, czyli 69% wskazań pozytywnych to FP |
| 10 | D | s. 49, §5.3 | Brak kropki na końcu: „Niezależna walidacja zewnętrzna na odrębnej próbie nie została przeprowadzona" |

### 3.2 Rozdziały 3–4

| # | Priorytet | Lokalizacja | Poprawka |
|---|---|---|---|
| 11 | **K** | s. 28, wzór (3.2) | Ujednolicić z `model_config.json` (zob. K2) |
| 12 | **K** | s. 28, §3.4.4 | Poprawić interpretację x₃ (zob. K4) |
| 13 | **K** | s. 46, Rys. 4.19 | Wygenerować raport ponownie aktualnym kodem (zob. K3) |
| 14 | W | s. 34, Rys. 4.1 | Podpis mówi „Zadanie 1: Czytanie tekstu", a bodziec na zrzucie to sześciowierszowa odprawa misji z linią „Naciśnij ENTER, aby kontynuować". Albo podmienić rysunek, albo dopisać, że bodźcem czytelniczym na stanowisku jest tekst fabularny — i wtedy skonfrontować to z Rys. 4.2 (siedem gęstych wierszy czeskiej prozy z ETDD70) |
| 15 | W | s. 30, §4.2.1 | Lista rejestrowanych parametrów wymienia tylko `TIME`, `TIME_TICK`, `BPOGX/Y/V`. Kod rejestruje dodatkowo `LPOGX/Y/V` i `RPOGX/Y/V`, a **cały argument o obuocznej odporności I2MC (Tab. 2.1, §4.4.1) opiera się właśnie na tych kanałach**. Uzupełnić listę |
| 16 | W | s. 25, §3.3.3 | Ten sam brak w opisie formatu „Dane surowe" — dopisać kanały jednooczne |
| 17 | W | s. 35, §4.4.7 | „w sytuacji braku pliku konfiguracyjnego **lub błędu jego odczytu**, automatycznie ładuje domyślny zestaw" — kod sprawdza wyłącznie `os.path.exists()`, nie ma bloku `try/except`. Uszkodzony JSON powoduje wyjątek, nie przejście na wartości awaryjne (zob. R3). Albo poprawić opis, albo poprawić kod |
| 18 | W | s. 35, §4.4.8 | Opisana procedura „ręcznego oznaczania" kolumny `is_dyslexic` nie odpowiada temu, co zrobiono: §5.1 podaje, że etykiety pobrano z `dyslexia_class_label.csv`, a repozytorium zawiera `dodaj_etykiety.py`, który robi to automatycznie. Opisać rzeczywisty przebieg |
| 19 | W | s. 17–19, §3.1.1 | Wykaz plików pomija `dodaj_etykiety.py` — jedyny brakujący moduł repozytorium, a zarazem element potoku treningowego |
| 20 | W | s. 21, Rys. 3.5 | Trzy nazwy plików niezgodne z kodem (zob. rozdz. 8, tabela Z-K) |
| 21 | W | s. 27–28, §3.4.3 | „niepewność rzędu ±10 cm przekłada się na ok. ±17%" — zależność jest asymetryczna: D = 50 cm daje **+20,0%**, D = 70 cm daje **−14,3%**. Podać obie wartości albo napisać „od −14% do +20%" |
| 22 | W | s. 22, §3.2.2 | Opóźnienie 100 ms między ekspozycją a startem rejestracji: (a) literówka „wystymowane" → „oszacowane"; (b) brak opisu metody pomiaru; (c) brak omówienia skutku — pierwsze ~100 ms czytania (w tym pierwsza fiksacja) systematycznie nie trafia do zapisu i nie jest nigdzie kompensowane |
| 23 | W | s. 23, §3.2.2 | Zadanie 2 opisane jako „filtr jakościowy danych", ale poprawna odpowiedź jest w kodzie **zaszyta na stałe jako „A"** (`experiment_module.py:178`). To istotne ograniczenie metodologiczne (brak kontrbalansowania), a praca go nie wymienia. README repozytorium wymienia je poprawnie |
| 24 | D | s. 24, §3.3.1 | „mała liczba parametrów (2)" — filtr 1€ ma trzy parametry, a kod ustawia wszystkie trzy (`mincutoff`, `beta`, `dcutoff=1.0`). Poprawić na „(3, z czego dwa wymagają strojenia)" |
| 25 | D | s. 22, §3.2.2 | „Akwizycja: Akwizycja: Rejestracja danych…" — powtórzone słowo |
| 26 | D | s. 26, §3.4.2 | „posród" → „pośród" |
| 27 | D | s. 33, §4.4.4 | „Generuje ona plik graficzny (`scanpath_*.png`)" — faktyczne nazwy to `#scanpath_<folder>.png` (indywidualna) i `<plik>_scanpath.png` (grupowa) |
| 28 | D | s. 32, §4.4.1 | Komentarz w kodzie podaje 60 Hz jako przykład częstotliwości bez dzielników z listy [2, 5, 10] — 60 dzieli się przez wszystkie trzy. Przykład jest błędny (dotyczy też `analysis_core.py:132`) |

### 3.3 Rozdziały 1–2

| # | Priorytet | Lokalizacja | Poprawka |
|---|---|---|---|
| 29 | W | s. 6 (§1.1) vs s. 8 (§2.1) | Ta sama liczba (31 868) opisana raz jako „zdający **z dostosowaniem warunków z tytułu dysleksji**", raz jako „uczniów **z dysleksją**". To nie są równoważne kategorie. Ujednolicić na pierwszą, węższą formułę |
| 30 | W | s. 6, §1.1 | Zestawienie „5–10% populacji szkolnej [1]" z „ponad 12% zdających [2]" pozostawione bez komentarza. Czytelnik dostaje dwie sprzeczne liczby; wystarczy zdanie wyjaśniające, że odsetek dostosowań maturalnych nie jest miarą chorobowości |
| 31 | W | s. 6, §1.2 | Cel „kalibracja i walidacja modelu na **zewnętrznym zbiorze referencyjnym**" koliduje z §5.3 („Niezależna **walidacja zewnętrzna** nie została przeprowadzona"). Termin „walidacja zewnętrzna" użyty w dwóch znaczeniach. Rozdzielić: „zbiór zewnętrzny" vs „walidacja zewnętrzna w sensie [36]" |
| 32 | W | s. 6, §1.2 | Cel „wykonanie pomiarów testowych" — zrealizowany wyłącznie na 10 dorosłych; §6.1 deklaruje osiągnięcie celu głównego. Doprecyzować, że pomiarów na grupie docelowej nie wykonano (§6.2 mówi to wprost, §6.1 nie) |
| 33 | D | s. 10, §2.6 | „Video-based Corneal Reflection - **VOCR**" — przyjęty skrót to **VCR** lub P-CR (pupil–corneal reflection) |
| 34 | D | s. 10, §2.6 | „efekt „czerwonych oczu)"" — nawias i cudzysłów w złej kolejności |
| 35 | D | s. 11, §2.7.1 | „średni czas w trakcie czytania u osoby dorosłej to zazwyczaj 225-325 ms [15]" — Rayner (2009) podaje ~225 ms **dla czytania**, ~275 ms dla przeszukiwania i ~330 ms dla percepcji scen. Przedział 225–325 miesza trzy paradygmaty; zawęzić do czytania |
| 36 | D | s. 11, §2.7.2 | „Sakady trwają zazwyczaj od 20 do 80 ms" — źródła [20,21,22] dotyczą tłumienia sakadowego, nie czasu trwania. Dodać źródło albo przenieść przypisy za drugą część zdania |
| 37 | D | s. 10, §2.5 | Brak spacji po odsyłaczach: „gałki ocznej [12].Kluczowym", „z otoczenia [16].Fundamentalnym", „około 1°-2°[13] podczas", „150°(90°skroniowo i 60°nosowo)" |
| 38 | D | s. 14, Tab. 2.2 vs s. 14 tekst | EyeLink 1000 Plus: tekst „dokładności sięgającej **poniżej** 0,15°", tabela „**do** 0,15° (typowo 0,25–0,50°)". Ujednolicić |
| 39 | D | s. 16–21, Rys. 3.1–3.5 | „Interface użytkownika" i podpis „architektury **interface'u** użytkownika" — polskie „interfejs" |
| 40 | D | s. 9, §2.4 | Dopisać, że badanie [11] przeprowadzono na dzieciach **szwedzkich** — praca omawia transfer językowy tylko w osi czeski→polski (§5.3.5), a zestaw cech pochodzi z jeszcze innego języka |

### 3.4 Usterki edytorskie w rozdziale 5

| # | Priorytet | Lokalizacja | Fragment | Poprawka |
|---|---|---|---|---|
| 41 | D | s. 47, §5.1 | „Do wyznaczenia współczynników, a następnie oceny skuteczności klasyfikacyjnej **Do badań wykorzystano** publiczny zbiór ETDD70…" | zdanie sklejone z dwóch, wielka litera w środku |
| 42 | D | s. 47, §5.1 | „(pliki `Subject_*_T4_Meaningful_Text_raw.csv`, po jednym na uczestnika, jako jedyne odpowiadające paradygmatowi…" | brak nawiasu zamykającego |
| 43 | D | s. 47, §5.1 | „…pliku `dyslexia_class_label.csv`**..**" | podwójna kropka |
| 44 | D | s. 48, §5.2 | „…(5 kobiet, 5 mężczyzn) **dla każdego uczestnika podano wynik P modelu.**" | brak interpunkcji między zdaniami składowymi |
| 45 | D | s. 50, §5.3.3 | „a optymalnie 400 uczestników **,** przy zrównoważonym podziale" | spacja przed przecinkiem |

---

## 4. Bibliografia

36 pozycji. Aparat jest zasadniczo poprawny i dobrany trafnie — literatura okulograficzna
(Rayner, Holmqvist/Nyström, Hessels, Salvucci–Goldberg, Engbert–Kliegl) jest właściwa
i aktualna. Uwagi dotyczą głównie spójności formatowania i kilku konkretnych wpisów.

### 4.1 Błędy wymagające poprawy

| Poz. | Problem | Poprawka |
|---|---|---|
| **[2]** | Tytuł i rok („Sprawozdanie z egzaminu maturalnego **2023**", 2023) są sprzeczne z treścią, do której się odwołuje (sesja **2025**), i z samym adresem URL (`.../2024/sprawozdanie/sprawozdanie_matura_**2025**_polski.pdf`) | Poprawić tytuł i rok na sprawozdanie za sesję 2025; dodać datę dostępu (pozostałe źródła internetowe ją mają) |
| **[33]** | „**1 C filter**: a simple speed-based low-pass filter…" — znak euro rozsypał się przy składzie | „1€ Filter" (w LaTeX-u: `1\euro{} Filter` lub `1\,€ Filter` z pakietem obsługującym znak) |
| **[6], [7]** | Baterie Dysleksja 3 i Dysleksja 5 opisane jako artykuły w czasopiśmie o nazwie „Dysleksja 3" / „Dysleksja 5" (`@article`) | To narzędzia diagnostyczne / podręczniki (Pracownia Testów Psychologicznych PTP). Zmienić typ wpisu na `@manual` lub `@book` i podać wydawcę — tak jak zrobiono w [8] |
| **[9]** | „Eye Tracking Methodology. 3rd." | Pełny tytuł: *Eye Tracking Methodology: Theory and Practice* |
| **[27]** | „R.S. Hessels, D.C. Niehorster, C. Kemner **i in.**" — praca ma dokładnie czterech autorów | Wypisać wszystkich (Hessels, Niehorster, Kemner, Hooge) — README repozytorium robi to poprawnie. Skrót „Behav Res" niespójny z pełnymi nazwami czasopism w pozostałych wpisach |
| **[34]** | DOI `10.5281/zenodo.17513247` (listopad 2025) | Zweryfikować, czy to DOI wersji, czy DOI koncepcyjny. Do cytowania stabilniejszy jest DOI koncepcyjny (rekord `13332134` figuruje jako główny wpis ETDD70). *Do weryfikacji przez autora* |
| **[3]** | Data dostępu 22.05.2024 przy pozostałych źródłach sieciowych z 5.09.2026 | Ujednolicić; przy okazji sprawdzić, czy „najnowsza klasyfikacja" odnosi się do aktualnego wydania ICD-11 |

### 4.2 Uwagi redakcyjne

- **Data dostępu przed rokiem wydania.** W [29]–[32] zapis ma postać „*URL*. dostęp: 5.09.2026. 2026."
  — data dostępu wypada przed rokiem. Konwencjonalna kolejność to rok, potem `(dostęp: …)`.
- **Rok 2026 dla stron producentów.** [29], [30], [32] mają rok 2026 (data pobrania), [31] rok 2017
  (data pliku PDF). Niekonsekwencja; przy stronach bez daty publikacji zwykle podaje się `b.d.`
  albo rok dostępu — ale konsekwentnie dla wszystkich czterech.
- **[35] vs [34].** Dwie pozycje o tym samym zbiorze mają różnych pierwszych autorów
  (Dostalova / Sedmidubsky). To możliwe (zbiór vs artykuł konferencyjny), ale warto sprawdzić
  zgodność z metadanymi Zenodo i SISAP.
- **Atrybucja instytucjonalna.** §5.1 przypisuje ETDD70 wyłącznie Uniwersytetowi Masaryka;
  zbiór powstał we współpracy z Uniwersytetem Duisburg-Essen.
- **Brak DOI** w [4], [6], [7], [8], [9], [10], [13], [14] — dla pozycji książkowych to dopuszczalne,
  ale warto uzupełnić ISBN tam, gdzie go nie ma ([6], [7]).

---

## 5. Powołania

Ocena, czy przypis w danym miejscu rzeczywiście podpiera zdanie, przy którym stoi.

### 5.1 Powołania poprawne i dobrze umiejscowione

| Miejsce | Źródło | Status |
|---|---|---|
| §2.4, liczebność 185 dzieci (97 + 88), wiek 9–10 | [11] | **✔ potwierdzone** (Benfatto i in. 2016, PLOS ONE) |
| §3.4.2, „ze 168 cech wyselekcjonowano 48" | [11] | **✔ potwierdzone** |
| §2.4, dokładność 95,6% | [11] | **✔ potwierdzone** (95,6% ± 4,5%) |
| §3.4.1, wartości domyślne I2MC (100 ms interpolacji, okno 200 ms, downsampling 2/5/10, min. fiksacja 40 ms) | [27] | **✔ potwierdzone w źródle biblioteki I2MC 2.2.8**: `windowtimeInterp=.1`, `windowtime=.2`, `downsamples=[2,5,10]`, `minFixDur=40.` |
| §5.3.3, próg 200 / optymalnie 400 uczestników | [36] | **✔ zgodne** z Collins, Ogundimu i Altman (2016) przy interpretacji 100+100 / 200+200 zdarzeń. Warto to doprecyzować w tekście |
| §6.2, „przy rozpowszechnieniu rzędu 10% większość wskazań pozytywnych to FP" | — | **✔ arytmetycznie poprawne**: PPV = 30,8%, czyli 69,2% wskazań pozytywnych to FP |
| §2.1, ICD-11 | [3] | ✔ nazwa jednostki zgodna z 6A03.0 |

### 5.2 Powołania wymagające weryfikacji lub przesunięcia

| Miejsce | Problem |
|---|---|
| §2.4: „czułość 95,5% oraz swoistość 95,7%" [11] | Dokładność 95,6% potwierdzona; pary czułość/swoistość **nie udało się zweryfikować** (dostęp do PLOS ONE i PMC zablokowany przez proxy). *Do sprawdzenia przez autora w oryginale* |
| §2.4: „okulografu Ober-2 pracującego z częstotliwością 100 Hz i z podparciem brody oraz czoła" | Niezweryfikowane z tego samego powodu. Twierdzenie o podparciu jest istotne, bo §3.4.2 buduje na nim argument o odrzuceniu czterech cech |
| §2.7.2: „Sakady trwają zazwyczaj od 20 do 80 ms [20, 21, 22]" | Przypisy dotyczą **tłumienia sakadowego**, nie czasu trwania. Zdanie zawiera dwa twierdzenia, przypis stoi za oboma |
| §2.7.1: „225-325 ms [15]" | Rayner (2009) rozróżnia paradygmaty; wartość dla czytania to ~225 ms |
| §3.4.1: pięć kolejnych zdań z tym samym przypisem [27] | Formalnie poprawne, ale nadmiarowe — wystarczy jedno powołanie na początek akapitu i zdanie zbiorcze na końcu (które zresztą jest) |
| §2.4: siedem wystąpień [11] w jednym podrozdziale | j.w. — warto skonsolidować |
| §5.1: „sposób rekonstrukcji sakad… zgodny z metodą zastosowaną przez autorów zbioru [35]" | Twierdzenie kluczowe dla porównywalności; niezweryfikowane (brak dostępu do Springer Link). *Do potwierdzenia* |

### 5.3 Twierdzenia bez powołania, które go wymagają

| Miejsce | Twierdzenie |
|---|---|
| §6.3 | Varjo XR-4: „częstotliwość próbkowania 200 Hz i sub-stopniowa dokładność poniżej 1°" — **żadnego źródła**, przy czterech innych urządzeniach opisanych z przypisami [29]–[32] |
| §3.2.1 | „Taka forma sprzyja utrzymaniu wysokiej koncentracji" — twierdzenie o skuteczności grywalizacji podane jako fakt. §6.1 uczciwie przyznaje, że nie było badane, ale §3.2.1 tego zastrzeżenia nie ma |
| §2.8 | Mapy ciepła, ścieżki wzroku, AOI — cały podrozdział bez ani jednego przypisu (naturalne odniesienie: Holmqvist i in., *Eye Tracking: A Comprehensive Guide to Methods and Measures*) |
| §2.7.3 | Podążanie płynne i ruchy wergencyjne — bez przypisu |
| §3.3.4 | „zbiór ETDD70, opublikowany na licencji Creative Commons Attribution 4.0 International" — bez odesłania do samej licencji/rekordu |
| §4.1 | Wykaz bibliotek (Pygame, pandas, numpy, I2MC) bez wersji i bez odniesień — README repozytorium ma pełną tabelę wersji, praca nie |
| §2.9 | Cała ocena porównawcza sprzętu opiera się na materiałach producentów [29]–[32]; brak niezależnego źródła weryfikującego deklarowane dokładności |

---

## 6. Brakujące źródła

Miejsca, w których praca dobrze zrobiłaby na dodaniu literatury — nie dlatego, że jest błędna,
lecz dlatego, że argument jest podparty słabiej niż mógłby być.

### 6.1 Luki merytoryczne

1. **Wynik referencyjny na tym samym zbiorze.** Autorzy ETDD70 raportują dokładność rzędu 90%
   na tych samych danych. Praca uzyskuje ~76–80% i **nigdzie tego nie porównuje**. To jest
   najważniejsza brakująca pozycja: recenzent zapyta o nią pierwszy. Porównanie działa na korzyść
   pracy — model tutaj ma 5 cech i jest interpretowalny, tamten używa metod AI o większej
   złożoności. Warto to napisać.

2. **Kryteria diagnostyczne DSM-5.** §2.1 opiera się wyłącznie na ICD-11. Dla pracy o przesiewie
   dysleksji standardem jest przywołanie obu klasyfikacji (DSM-5, 315.00 / F81.0), zwłaszcza że
   literatura anglojęzyczna, na której praca się opiera ([11]), operuje kategoriami DSM.

3. **Metodologia sprawozdawcza modeli predykcyjnych.** Praca stosuje wytyczne z [36] do
   liczebności próby, ale nie powołuje się na **TRIPOD** (Collins i in. 2015) — standard
   raportowania modeli predykcyjnych. To ten sam pierwszy autor, więc uzupełnienie jest naturalne
   i podniosłoby ocenę rozdziału 5.

4. **Niezależne pomiary dokładności okulografów.** Do §2.9 warto dołożyć pracę weryfikującą
   parametry producentów w warunkach rzeczywistych — deklaracje marketingowe i wyniki niezależne
   różnią się istotnie, a praca sama argumentuje z tych parametrów.

5. **Przejrzystość ortograficzna języka.** §5.3.5 argumentuje różnicą przejrzystości ortografii
   czeskiej i polskiej — to twierdzenie **bez źródła**, a istnieje na nie obszerna literatura
   (m.in. Seymour, Aro i Erskine 2003 o przyswajaniu czytania w ortografiach europejskich).
   Argument jest trafny, brakuje mu tylko podparcia.

6. **Odporność testów przesiewowych na symulację.** §5.2 to jeden z najciekawszych fragmentów
   pracy i jest całkowicie pozbawiony kontekstu literaturowego. Zagadnienie ma nazwę
   (*malingering*, *performance validity*) i własną literaturę — powołanie ustawiłoby ten
   podrozdział jako świadomy wkład, a nie obserwację przypadkową.

7. **Alternatywa dla rekonstrukcji sakad.** §3.4.2 uzasadnia odrzucenie czterech cech
   ograniczeniami sprzętu. Warto wskazać, że istnieją algorytmy detekcji sakad działające
   na zaszumionym sygnale — praca sama je wymienia w Tab. 2.1 ([25] Nyström & Holmqvist,
   [26] REMoDNaV) — i wyjaśnić, dlaczego nie użyto ich **równolegle** z I2MC do odzyskania
   parametrów dynamicznych. Obecnie czytelnik odnosi wrażenie, że wybór I2MC wykluczył
   tę możliwość, co nie jest prawdą.

### 6.2 Braki w warstwie danych (nie literatury)

| Czego brakuje | Skutek |
|---|---|
| Plik cech z etykietami użyty do finalnego treningu (`8b730cd`) | Model w repozytorium jest **nieodtwarzalny** |
| Kod liczący macierz pomyłek | Tab. 5.1 nie ma źródła w kodzie |
| Surowe wyniki testów odpornościowych (10 dorosłych) | Tab. 5.2 nieweryfikowalna |
| Charakterystyka jakości sygnału (odsetek utraconych próbek, liczba fiksacji per uczestnik) | Brak podstawy dla twierdzeń §5.3.4 i §6.1 o stabilności akwizycji |
| Bodziec tekstowy (`tekst_badawczy.txt`) | Nie da się ocenić porównywalności z bodźcem ETDD70 — kluczowej dla §5.3.5 |

---

## 7. Pozycje do korekty

Zestawienie wyłącznie językowo-redakcyjne, uporządkowane wg stron.

| Strona | Fragment | Poprawka |
|---|---|---|
| 10 | „gałki ocznej [12].Kluczowym elementem" | brak spacji po odsyłaczu |
| 10 | „zaledwie około 1°-2°[13] podczas gdy" | brak spacji przed i po odsyłaczu; myślnik → półpauza |
| 10 | „w poziomie na ok. 150°(90°skroniowo i 60°nosowo)" | brak spacji po znaku stopnia (3×) |
| 10 | „z otoczenia [16].Fundamentalnym założeniem" | brak spacji |
| 10 | „efekt „czerwonych oczu)”" | → „efekt „czerwonych oczu”)" |
| 10 | „**VOCR**" | → „VCR" |
| 12 | „umieszczone w tabeli 2.1 Do najpopularniejszych" | brak kropki po numerze tabeli |
| 16–21 | „Interface użytkownika" (Rys. 3.1–3.5) | → „Interfejs użytkownika" |
| 20 | „architektury interface'u użytkownika" (podpis Rys. 3.4) | → „interfejsu" |
| 21 | „`weryfikacje_dane_surowe.csv`", „`weryfikacje_zdarzenia.csv`", „`gra_dane_zdarzenia.csv`" (Rys. 3.5) | → `weryfikacja_dane_surowe.csv`, `weryfikacja_zdarzenia.csv`, `gra_zdarzenia.csv` |
| 21 | „`tlo_kokpitu.jpg`" (Rys. 3.5) | → `tlo_kokpit.jpg` |
| 22 | „• Akwizycja: **Akwizycja:** Rejestracja danych" | usunąć powtórzenie |
| 22 | „zostało **wystymowane** na 100 ms" | → „oszacowane" |
| 23 | „do późniejszej **nałożenia** map fiksacji" | → „do późniejszego nałożenia" |
| 25 | „(`weryfikacja_zdarzenia.csv`, `gra_dane_zdarzenia.csv`)" | drugi plik nazywa się `gra_zdarzenia.csv` |
| 26 | „**posród** których 9 cech" | → „pośród" |
| 27 | „**Przy zbyt małej** dokładności bazowej okulografu" | zdanie bardzo długie (5 wierszy) — rozbić |
| 28 | „±17% wartości cech v4 i v5" | → „od −14% do +20%" (zob. poz. 21) |
| 31 | „`zrzut_ekranu_bodzca.png`), który jest niezbędny do późniejszej nałożenia ścieżek wzroku" | → „do późniejszego nałożenia" |
| 33 | „obliczane są :" | spacja przed dwukropkiem |
| 47 | „…oceny skuteczności klasyfikacyjnej **Do badań wykorzystano**…" | dwa zdania sklejone |
| 47 | „(pliki `Subject_*_T4_Meaningful_Text_raw.csv`, …, jako jedyne odpowiadające paradygmatowi realizowanemu w Zadaniu 1 opracowanego stanowiska." | brak nawiasu zamykającego |
| 47 | „`dyslexia_class_label.csv`**..**" | podwójna kropka |
| 48 | „(5 kobiet, 5 mężczyzn) dla każdego uczestnika podano wynik P modelu." | brak interpunkcji |
| 49 | „…nie została przeprowadzona" | brak kropki |
| 50 | „optymalnie 400 uczestników **,** przy" | spacja przed przecinkiem |
| 51 | „wszystkie etapy sesji **–od** wprowadzenia" | brak spacji po półpauzie |
| 52 | „większość wskazań pozytywnych **stanowiłyby**" | → „stanowiłaby" |
| 52 | „**bądź** mieszanej ze zintegrowanym śledzeniem" | → „bądź rzeczywistości mieszanej" (elipsa utrudnia odczyt) |
| całość | Zapis „I2MC" vs „Identification by two-means clustering" | Praca konsekwentnie rozwija skrót w rozdziałach 3–4, ale w Tab. 2.1 i §5.3.4 używa skrótu. Ujednolicić: rozwinąć przy pierwszym użyciu, dalej skrót |

---

## 8. Zgodność kod – tekst

Systematyczne porównanie twierdzeń pracy z repozytorium @ `1e8ecad`.

### 8.1 Zgodność potwierdzona ✔

| Twierdzenie pracy | Miejsce w kodzie | Status |
|---|---|---|
| Wzór (4.1): ΔT = T_PC − T_tracker, potem T = ΔT + T_tracker | `gazepoint.py:322` | ✔ `anchor_pc + (tracker_time - anchor_tracker)` — algebraicznie tożsame |
| Wzór (3.1): θ = 2·arctan(dist/(2·D))·180/π | `analysis_core.py:45` | ✔ `2*np.degrees(np.arctan(dist_cm/(2*VIEWING_DISTANCE_CM)))` |
| Wzór (3.3): P = 1/(1+e^−Z) | `analysis_core.py:488` | ✔ |
| Próg klasyfikacji P > 0,5 | `analysis_core.py:494` | ✔ |
| Kalibracja 9-punktowa (siatka 3×3) | `gazepoint.py:207-213` | ✔ `CALIBRATION_MARGIN=0.1` → `(0.1, 0.5, 0.9)²` = 9 punktów |
| Powtarzany stratyfikowany CV, 7 podziałów, 5 powtórzeń | `model_trainer.py:101` | ✔ `RepeatedStratifiedKFold(n_splits=7, n_repeats=5)` |
| Standaryzacja dopasowywana tylko na foldzie treningowym | `model_trainer.py:98` | ✔ `Pipeline([scaler, logreg])` — brak przecieku danych |
| Parametry I2MC = wartości domyślne biblioteki | `analysis_core.py:137-157` | ✔ zweryfikowane w źródle I2MC 2.2.8 |
| `INTERP_MAX_GAP_MS = 100`, `WINDOW_SIZE_MS = 200` | `analysis_core.py:21-22` | ✔ |
| Min. czas fiksacji 40 ms z domyślnych I2MC | `analysis_core.py:23-24` | ✔ `minFixDur` nieustawiany, domyślna 40.0 |
| Downsampling dobierany dynamicznie (2, 5, 10) | `analysis_core.py:129-134` | ✔ |
| `ProcessPoolExecutor`, obejście GIL | `analysis_group.py:157` | ✔ |
| `matplotlib.use('Agg')` + `plt.close('all')` | `analysis_group.py:7, 126, 130` | ✔ |
| `itertuples` zamiast `iterrows` | `analysis_core.py:301-303` | ✔ |
| Parametry filtra 1€: β = 0,9, f_min = 0,04 | `experiment_config.py:87-88` | ✔ |
| TCP 127.0.0.1:4242, XML, `ENABLE_SEND_DATA` | `experiment_config.py:85-86`, `gazepoint.py:65` | ✔ |
| Wątek demon do logowania | `gazepoint.py:279` | ✔ |
| `HWSURFACE` + `DOUBLEBUF` | `experiment_module.py:16` | ✔ |
| Marginesy 15% poziomo / 10% pionowo | `experiment_config.py:63-64` | ✔ |
| Cel w narożnikach i centrum | `experiment_module.py:217-223` | ✔ 5 pozycji |
| Zapis behawioralny z dokładnością do 3 miejsc | `experiment_main.py:17` | ✔ `round(reaction_time, 3)` |
| Foldery `<kryptonim>_<timestamp>`, UTF-8 | `experiment_main.py:32-35` | ✔ |
| Zadanie czytania nie zapisuje pliku zdarzeń | `experiment_module.py:141` | ✔ `save_events=0` |
| Sakada bez własnego czasu trwania | `analysis_core.py:335` | ✔ `duration_samples: 0` |

### 8.2 Rozbieżności (Z-K)

| # | Twierdzenie pracy | Stan kodu | Waga |
|---|---|---|---|
| **ZK1** | Wzór (3.2): intercept 0,272; β = [1,707; 1,041; −0,329; 0,764; −0,165] | `model_config.json`: 0,295; [1,509; 1,162; −0,115; 0,720; −0,139] | **krytyczna** |
| **ZK2** | §5.1.1: czułość/swoistość/dokładność 80,0% | `model_trainer.py` na odzyskanym zbiorze: 73,7 / 77,7 / 75,7% | **krytyczna** |
| **ZK3** | Rys. 4.19: raport z cechami w px i wynikiem 0,000 | Kod drukuje poz. 6 z jednostką `deg` i dodaje wiersz „Tryb segmentacji" | **krytyczna** |
| **ZK4** | §4.2.1 i §3.3.3: rejestrowane są `TIME`, `TIME_TICK`, `BPOGX/Y/V` | `gazepoint.py:71-84`: dodatkowo `LPOGX/Y/V`, `RPOGX/Y/V` — kanały, na których opiera się cały argument o obuocznej odporności I2MC | wysoka |
| **ZK5** | §4.4.7: przy braku pliku **lub błędzie odczytu** ładowany jest zestaw awaryjny | `analysis_core.py:432-437`: sprawdzane jest tylko `os.path.exists()`; uszkodzony JSON rzuca wyjątek | wysoka |
| **ZK6** | §4.4.8: etykiety nanoszone ręcznie | Repozytorium zawiera `dodaj_etykiety.py`, a §5.1 mówi, że etykiety wzięto z `dyslexia_class_label.csv` | wysoka |
| **ZK7** | §3.1.1: wykaz plików systemu | Pomija `dodaj_etykiety.py` | średnia |
| **ZK8** | Rys. 3.5: `weryfikacje_dane_surowe.csv`, `weryfikacje_zdarzenia.csv`, `gra_dane_zdarzenia.csv`, `tlo_kokpitu.jpg` | `weryfikacja_dane_surowe.csv`, `weryfikacja_zdarzenia.csv`, `gra_zdarzenia.csv`, `tlo_kokpit.jpg` | średnia |
| **ZK9** | §3.2.2: pytanie weryfikacyjne jako „filtr jakościowy" | `experiment_module.py:178`: `is_correct = (user_answer == 'A')` — poprawna odpowiedź zaszyta na stałe | średnia |
| **ZK10** | §4.5.2: `_get_center_geometry` centruje okna dialogowe na wybranym ekranie | `tkinter_module.py:8`: funkcja jest używana **wyłącznie** dla okna raportu; okna dialogowe używają `_setup_fullscreen_bg`. Komentarz w kodzie mówi to wprost | niska |
| **ZK11** | §4.5.3: `experiment_config.py` jako „jedno źródło prawdy" | `gazepoint.py:42`: `'freq': 150` zaszyte na stałe zamiast `experiment_config.EYETRACKER_FREQ`; `analysis_core.py:9-12` ma własny, niezależny komplet stałych ekranu | niska |
| **ZK12** | §3.3.1: filtr 1€ ma „małą liczbę parametrów (2)" | `gazepoint.py:41-46`: ustawiane są trzy (`mincutoff`, `beta`, `dcutoff`) | niska |
| **ZK13** | §4.4.4: `scanpath_*.png` | `#scanpath_<folder>.png` (indywidualna), `<plik>_scanpath.png` (grupowa) | niska |
| **ZK14** | §5.1: „wykorzystano wyłącznie zapisy zadania czytania tekstu ciągłego (T4)" | `analysis_group.py:148`: wzorzec `Subject_*_raw.csv` dopasowuje **wszystkie** zadania (T1–T5). Ograniczenie do T4 jest wyłącznie konwencją operatora, nieegzekwowaną przez kod | średnia |
| **ZK15** | §3.2.2 / Rys. 4.1: „Zadanie 1: Czytanie tekstu" na tekście ciągłym | Bodziec na Rys. 4.1 to sześciowierszowa odprawa misji zakończona „Naciśnij ENTER, aby kontynuować"; Rys. 4.19 raportuje 28 fiksacji z tej sesji, przy siedmiu gęstych wierszach prozy w ETDD70 (Rys. 4.2) | wysoka |

### 8.3 Zgodność praca ↔ README

README repozytorium jest **dokładniejszy niż praca** w kilku punktach i sam odnotowuje część
powyższych rozbieżności (sekcja 13 „Znane ograniczenia" wymienia zaszytą odpowiedź „A",
niedopasowanie stałych ekranu, mylące etykiety „px" w raporcie, ręczną synchronizację wag
awaryjnych). Warto przenieść te zastrzeżenia do pracy — obecnie repozytorium jest wobec
własnych ograniczeń bardziej krytyczne niż tekst dyplomu.

Dwie rozbieżności README ↔ praca:
- README numeruje grę sakadową jako „Zadanie 2", praca jako „Zadanie 3" (README pomija
  pytanie weryfikacyjne w numeracji zadań).
- README §9.3 podaje wagi HEAD (1,509…), praca — wagi `bd60e47` (1,707…). Zob. ZK1.

---

## 9. Ryzyka w kodzie

Uporządkowane wg wpływu na wynik naukowy, nie wg trudności naprawy.

### R1 — Rozjazd między `model_config.json` a zestawem awaryjnym *(wysokie)*

`analysis_core.py:439-460` przechowuje kopię wag i tabeli `STATS`, używaną, gdy
`model_config.json` nie zostanie znaleziony. Ścieżka jest **względna** (`"model_config.json"`),
więc uruchomienie z innego katalogu roboczego po cichu przełącza model na zestaw wbudowany.
Obecnie oba zestawy są zsynchronizowane (commit `93bc348`), ale synchronizacja jest ręczna —
kod, README i komentarz w samym pliku zgodnie ostrzegają, że po każdym przetrenowaniu trzeba
ją powtórzyć.

**Skutek:** dwa różne wyniki dla tego samego pliku wejściowego, bez żadnego sygnału dla operatora.

**Naprawa:** rozwiązać ścieżkę względem `__file__`, a nie CWD:
```python
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.json")
```
i zamienić zestaw awaryjny na twardy błąd (`FileNotFoundError` z czytelnym komunikatem).
Cicha degradacja modelu diagnostycznego jest gorsza niż zatrzymanie analizy.

---

### R2 — Geometria ekranu zaszyta pod zbiór ETDD70 *(wysokie)*

`analysis_core.py:9-12`:
```python
SCREEN_WIDTH  = 1680
SCREEN_HEIGHT = 1050
SCREEN_WIDTH_CM = 47.4
VIEWING_DISTANCE_CM = 60.0
```
`analysis_individual.py:28-31` skaluje znormalizowane współrzędne GP3 (0–1) przez te stałe:
```python
clean_df['x'] = df['LPOGX'] * core.SCREEN_WIDTH   # 1680
clean_df['y'] = df['LPOGY'] * core.SCREEN_HEIGHT  # 1050
```
Stanowisko pracuje w **1920×1080 (16:9)**, a stałe opisują ekran **16:10**. Zakładana wysokość
ekranu wynosi 47,4 · 1050/1680 = **29,62 cm**, podczas gdy monitor 16:9 o szerokości 47,4 cm
ma wysokość **26,66 cm**.

**Skutek:** pionowe DVA jest dla danych ze stanowiska **zawyżone o 11,1%**. Dotyczy to cechy
`sac_prog_y_stab` (x₄), która w modelu ma dodatnią wagę +0,76 — błąd przesuwa wynik
systematycznie **w stronę „wysokiego ryzyka"**. Wartości P w Tab. 5.2 (testy odpornościowe)
są tym obciążone.

**Naprawa:** przenieść geometrię do parametrów wywołania (praca sama zapowiada to w §3.4.3
i §6.1). Warto przy tym wykorzystać wbudowaną obsługę w I2MC — biblioteka przyjmuje `scrSz`
i `disttoscreen` i sama zwraca statystyki fiksacji w stopniach (`I2MC.py:145-146`,
`get_fix_stats(..., pix_per_deg)`), więc własna funkcja `px_to_dva` jest w dużej mierze
duplikatem istniejącej funkcjonalności.

---

### R3 — Uszkodzony `model_config.json` przewraca analizę zamiast degradować *(średnie)*

`analysis_core.py:432-437` nie ma bloku `try/except` wokół `json.load()`. Uszkodzony,
obcięty lub niekompletny plik (brak klucza `STATS`) rzuca wyjątek, który:
- w analizie **grupowej** zostaje przechwycony przez szerokie `except Exception`
  (`analysis_group.py:141`) i uczestnik **wypada z raportu bez żadnego ostrzeżenia** —
  w `#wyniki_grupowe.csv` po prostu zabraknie wiersza;
- w analizie **indywidualnej** zwraca komunikat o błędzie.

To bezpośrednio przeczy §4.4.7 (zob. ZK5).

**Naprawa:** opakować odczyt w `try/except (json.JSONDecodeError, KeyError)` i zalogować
przejście na zestaw awaryjny (albo — zgodnie z R1 — przerwać z jasnym komunikatem).
Niezależnie: `analysis_group.py:141` powinien logować typ wyjątku i nazwę pliku, a liczba
pominiętych uczestników powinna trafiać do komunikatu końcowego.

---

### R4 — Niespójna walidacja próbek między dwoma potokami *(średnie)*

| Potok | Kryterium |
|---|---|
| `analysis_individual.py:55-62` | zakres 0–1 **oraz** flaga `POGV == 1` |
| `analysis_group.py:50` | wyłącznie `(x > 1) & (y > 1)` |

Potok grupowy **nie ma górnego ograniczenia**: próbka o współrzędnej 5000 px (poza ekranem)
przechodzi jako poprawna i trafia do klastrowania. Dodatkowo odrzuca poprawne próbki
w lewym górnym rogu (x ≤ 1 px).

**Skutek:** wyniki dla zbioru referencyjnego i dla danych ze stanowiska nie powstają
przez identyczny filtr — a §5.1 argumentuje właśnie identycznością potoku
(„aby zapewnić identyczność potoku przetwarzania dla zbioru referencyjnego i dla danych
rejestrowanych na opracowanym stanowisku").

**Naprawa:** wydzielić wspólną funkcję walidacji do `analysis_core.py` i wywoływać ją z obu
potoków, z parametrem określającym układ współrzędnych (piksele vs znormalizowane).

---

### R5 — Kolinearność cech + wyłączona regularyzacja *(średnie, naukowe)*

`model_trainer.py:93`: `LogisticRegression(C=np.inf)` — regularyzacja jest **celowo wyłączona**,
z uzasadnieniem, że „wagi trafiają wprost do `model_config.json`, więc nie mogą być ściągnięte
przez żadną karę". Przy r(x₁, x₃) = 0,86 i r(x₂, x₅) = −0,62 skutkuje to wagami niestabilnymi
(zob. K4: β₃ zmienia znak w 17% foldów, β₅ w 20%).

**Naprawa:** albo dodać regularyzację L2 z doborem C w wewnętrznej pętli CV, albo — prościej
i bez zmiany modelu — **zaraportować rozrzut wag między foldami** w pracy. To drugie rozwiązanie
nic nie kosztuje, a zamienia słabość w świadomie opisane ograniczenie. `model_trainer.py` ma
już wszystkie potrzebne dane (`cv_results['estimator']`), wystarczy dopisać `np.std` obok `np.mean`.

---

### R6 — Model raportowany ≠ model wdrożony *(średnie, metodologiczne)*

`model_trainer.py:132-140` uśrednia wagi i statystyki `STATS` z 35 foldów i zapisuje je jako
model produkcyjny. Metryki raportowane w §5.1.1 pochodzą natomiast z **modeli fold-owych**,
z których każdy był trenowany na 6/7 danych i miał własne wagi. Model uśredniony nigdy nie był
oceniany out-of-sample.

Empirycznie różnica nie jest duża (uśredniony model daje w resubstytucji 27/8/7/28), ale
formalnie **czułość i swoistość podane w pracy nie opisują modelu zapisanego w `model_config.json`**.

**Naprawa:** dopisać do §3.4.4 lub §5.1 jedno zdanie: „Wagi produkcyjne powstają przez
uśrednienie współczynników z 35 foldów; raportowane metryki dotyczą modeli fold-owych
i stanowią oszacowanie górnej granicy zgodności dla modelu uśrednionego."
Alternatywnie: dopasować model finalny na całym zbiorze i to jego wagi eksportować
(jest to praktyka bardziej standardowa).

---

### R7 — Wzorzec `Subject_*_raw.csv` nie odróżnia zadań *(niskie, ale wpływa na odtwarzalność)*

`analysis_group.py:148` dopasowuje wszystkie pliki `Subject_*_raw.csv`. W ETDD70 pasują do niego
zapisy zadań T1 (sylaby), T4 (tekst ciągły) i T5 (pseudo-tekst). Umieszczenie w katalogu zbioru
w całości daje po cichu wyniki z trzech różnych paradygmatów w jednym `#wyniki_grupowe.csv`.

**Naprawa:** parametr `--task` lub konfigurowalny wzorzec, domyślnie `Subject_*_T4_Meaningful_Text_raw.csv`.
Alternatywnie: wypisywać na końcu listę faktycznie przetworzonych zadań.

---

### R8 — Etykiety jednostek i nazw w raporcie indywidualnym *(niskie)*

`analysis_individual.py:181, 189-190`:
```python
f"Częstotliwość próbkowania: {sample_rate_ms:.2f} ms\n"     # to okres, nie częstotliwość
f"4. Śr. dystans sakad PROG: {...:.2f} px\n"                 # wartość jest w DVA
f"5. Max zakres sakad PROG:  {...:.2f} px\n"                 # wartość jest w DVA
```
Trzy błędne etykiety w raporcie, który praca przedstawia jako produkt końcowy (Rys. 4.19)
i który README wymienia w „Znanych ograniczeniach". Poprawka to trzy znaki.

---

### R9 — Anonimizacja: dane osobowe widoczne na Rys. 4.19 *(niskie technicznie, istotne formalnie)*

§3.3.4 deklaruje: *„identyfikatory uczestników mają postać pseudonimów, a rejestrowane pliki
nie zawierają danych umożliwiających identyfikację osoby"*. Rys. 4.19 pokazuje ścieżkę:

```
C:/Users/jusus/Desktop/PBD/dane_z_badan/Jerzy_2026-04-14_00-19-07/...
```

Identyfikator uczestnika to imię („Jerzy"), a nie pseudonim; widoczna jest też nazwa konta
systemowego. Ten sam identyfikator pojawia się w tytule wykresu na Rys. 4.1.

**Naprawa:** wygenerować rysunki ponownie na danych z identyfikatorem pseudonimowym
(np. `kadet_01`) — i tak trzeba je odtworzyć z powodu K3. Kod nie wymusza pseudonimizacji
(`experiment_main.py:31` czyści tylko znaki niealfanumeryczne); warto dopisać do
`get_participant_id` komunikat, że pole nie może zawierać danych osobowych.

---

### R10 — Drobne *(niskie)*

| Miejsce | Uwaga |
|---|---|
| `gazepoint.py:42` | `'freq': 150` zaszyte zamiast `experiment_config.EYETRACKER_FREQ` |
| `analysis_core.py:132` | Komentarz podaje 60 Hz jako przykład częstotliwości bez dzielników z [2,5,10]; 60 dzieli się przez wszystkie trzy |
| `analysis_group.py:155-156` | Komunikat „przetwarzania wielowątkowego" — użyto procesów, nie wątków (praca w §4.4.5 opisuje to poprawnie) |
| `analysis_core.py:429` | `model_config.json` wczytywany przy **każdym** wywołaniu `calculate_risk_score` — w analizie grupowej raz na uczestnika. Podmiana pliku w trakcie przebiegu da niejednorodne wyniki |
| `analysis_individual.py:134`, `analysis_group.py:115` | Rozmiar znacznika = `duration_samples * 2` — zależny od częstotliwości próbkowania, więc wykresy z różnych urządzeń nie są porównywalne wizualnie |
| `analysis_individual.py:118` / `analysis_group.py:117` | `if f == fixations[0]` — porównanie słowników przez wartość; dwie identyczne fiksacje dostaną ten sam kolor |
| `experiment_module.py:71` | `lines.append(current_line.strip())` poza pętlą po słowach dokłada pusty wiersz dla pustych akapitów |
| `tkinter_module.py:174` | `wait_for_calibration_confirmation()` używa monitora 0 zamiast wybranego przez operatora |
| `experiment_module.py` | Zdarzenia logowane przez `time.time()`, a przebieg gry mierzony `pygame.time.get_ticks()` — dwa zegary w jednym pliku zdarzeń |
| `analysis_core.py:75` | Autodetekcja jednostki czasu (`< 1.0` → sekundy) zawiedzie dla urządzeń > 1000 Hz ze znacznikami w ms; kontrola zakresu 20–2000 Hz łapie tylko część przypadków |

---

## 10. Ocena końcowa

### 10.1 Mocne strony

- **Rozdziały 5 i 6 są napisane uczciwie.** Praca sama nazywa brak walidacji zewnętrznej,
  pełną podatność modelu na symulację objawów, problem wartości predykcyjnej dodatniej przy
  niskiej chorobowości i barierę transferu językowego. §6.2 wprost odmawia nazwania systemu
  „gotowym narzędziem przesiewowym". To jest rzadkie i podnosi wiarygodność całości.
- **Testy odpornościowe (§5.2) to samodzielny wkład.** Sprawdzenie, czy badany może udawać
  objawy, nie jest standardowym elementem prac tego typu, a wynik (10/10 skutecznych symulacji)
  jest istotny praktycznie.
- **Warstwa inżynierska jest solidna.** Ustalone ziarno RNG dla I2MC z udokumentowanym
  uzasadnieniem (rozstęp oceny do 0,13 bez ziarna), poprawka `maxdisp`, oznaczanie braków jako
  NaN zamiast usuwania wierszy, jawny status „BŁĄD SEGMENTACJI" zamiast fałszywie niskiego
  ryzyka, weryfikacja ACK komend kalibracji, `Pipeline` bez przecieku danych w CV —
  to są decyzje świadome, nie przypadkowe.
- **README repozytorium** (535 wierszy) jest dokumentacją lepszą niż w większości prac
  dyplomowych i sam odnotowuje część ograniczeń.
- **Dobór algorytmu i cech jest uzasadniony merytorycznie**, a odrzucenie czterech z dziewięciu
  cech z [11] wraz z argumentacją sprzętową (§3.4.2) to dojrzały fragment.

### 10.2 Słabości

- **Rozdział 5 nie jest odtwarzalny.** Liczby w Tab. 5.1 nie wychodzą z żadnego artefaktu
  w repozytorium; plik cech dla finalnego modelu nie został zachowany; kodu liczącego macierz
  pomyłek nie ma. To najpoważniejszy zarzut wobec pracy.
- **Rozdział 4 dokumentuje trzy różne wersje systemu.** Równanie (3.2), zawartość repozytorium
  i Rys. 4.19 pochodzą z trzech różnych momentów rozwoju projektu.
- **Interpretacja x₃ jest sprzeczna z danymi**, a interpretacje x₃ i x₅ opierają się na
  współczynnikach nieodróżnialnych od zera.
- **Brak porównania z wynikiem referencyjnym** autorów ETDD70 na tych samych danych.
- **Rozdział 2 ma niższą precyzję cytowania** niż reszta pracy — kilka twierdzeń bez źródeł,
  §2.8 bez ani jednego przypisu, przypisy stojące za zdaniami, których nie podpierają.

### 10.3 Ocena wymiarowa

| Wymiar | Ocena | Uzasadnienie |
|---|---|---|
| Spójność logiczna wywodu | **3,5 / 5** | Struktura poprawna, ale kolizja „walidacja zewnętrzna" §1.2 ↔ §5.3, błędna atrybucja w §5.3.1, rozejście streszczeń PL/EN, interpretacja x₃ przeciwna do danych |
| Precyzja cytowania | **3,5 / 5** | Dobór literatury trafny; usterki w [2], [6], [7], [33], przypisy niepodpierające zdań w §2.7.2, kilka twierdzeń bez źródeł (Varjo, grywalizacja, §2.8) |
| Zgodność dokumentacji z kodem | **2,5 / 5** | 15 rozbieżności, w tym trzy krytyczne; równanie modelu w pracy ≠ model w repozytorium |
| Odtwarzalność wyników | **2 / 5** | Główny wynik pracy nie odtwarza się z materiału źródłowego; brak pliku danych dla finalnego modelu |
| Jakość implementacji | **4 / 5** | Świadome decyzje inżynierskie, dobra dokumentacja, sensowna obsługa błędów; minusem geometria zaszyta pod jeden zbiór i niespójna walidacja próbek |
| Uczciwość w dyskusji ograniczeń | **5 / 5** | Wzorcowa — §5.3 i §6.2 są mocniejsze niż w wielu pracach magisterskich |
| Redakcja i język | **3 / 5** | Ok. 30 usterek edytorskich, w tym trzy zdania sklejone lub niedokończone w rozdziale 5 |

### 10.4 Rekomendacja

**Praca nadaje się do obrony po wykonaniu poprawek krytycznych K1–K6.**

Żadna z tych poprawek nie wymaga powtórzenia badań ani przebudowy systemu:

- **K1** — przeliczenie metryk (uruchomienie istniejącego skryptu) i przepisanie Tab. 5.1;
  jeśli 80/80/80 ma zostać, trzeba dołączyć plik danych, z którego te liczby powstały.
- **K2** — decyzja, która wersja modelu jest wersją pracy, i ujednolicenie czterech miejsc.
- **K3** — ponowne wygenerowanie jednego zrzutu ekranu.
- **K4** — przepisanie dwóch akapitów interpretacyjnych; dane potrzebne do nowej wersji
  są w niniejszej recenzji.
- **K5** — tłumaczenie aktualnego streszczenia polskiego.
- **K6** — przepisanie jednego punktu w §5.3.1.

Nakład: **jeden–dwa dni pracy redakcyjnej** plus jedno uruchomienie skryptu treningowego.

Po wykonaniu K1–K6 i przynajmniej pozycji oznaczonych **W** z rozdziału 3, praca będzie
rzetelnym opracowaniem inżynierskim, którego największym atutem pozostanie to, co już ma:
świadomość własnych ograniczeń wyrażona wprost, a nie ukryta.

**Jedna uwaga na koniec.** Sekcja 13 README („Znane ograniczenia") jest ostrzejsza wobec
projektu niż tekst dyplomu. Przeniesienie jej zawartości do rozdziału 5 pracy niczego nie
zepsuje, a usunie większość rozbieżności z rozdziału 8 niniejszej recenzji — bo autor
te problemy już zna i już je opisał. Tylko nie w pracy.
