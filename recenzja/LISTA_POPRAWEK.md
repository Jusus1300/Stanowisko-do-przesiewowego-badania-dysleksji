# Lista poprawek — do odhaczania

Osiem etapów w **kolejności zależności**: napraw dane i kod, zanim zaczniesz poprawiać
liczby w tekście. 85 punktów, w tym 21 krytycznych.

Pełne uzasadnienie każdego punktu: [`RECENZJA_PRACY.md`](RECENZJA_PRACY.md).
Wersja klikalna z zapisywanym stanem: artefakt „Lista poprawek dyplomu".

Legenda priorytetów: **K** — bez tego praca zawiera twierdzenie nieprawdziwe lub
nieweryfikowalne · **W** — miejsce na niewygodne pytanie recenzenta · **D** — drobne.

---

## ETAP 0 — Decyzje przed startem

Dwa rozstrzygnięcia, od których zależy cała reszta. Dopóki nie zapadną, nie ma sensu
poprawiać liczb w tekście.

- [ ] **0.1 (K) Zdecyduj, która wersja modelu jest wersją pracy** — `model_config.json`, historia git

  | commit | b₀ | β₁ | β₂ | β₃ | β₄ | β₅ | status |
  |---|---|---|---|---|---|---|---|
  | `ad66f15` | 0,322 | 1,888 | 0,879 | −0,262 | 0,879 | −0,163 | pierwszy commit |
  | `bd60e47` | 0,272 | 1,707 | 1,041 | −0,329 | 0,764 | −0,165 | **= wzór (3.2) w pracy** |
  | `8b730cd` | 0,295 | 1,509 | 1,162 | −0,115 | 0,720 | −0,139 | stan HEAD repozytorium |

  Wybierz jeden i trzymaj się go do końca — od tej decyzji zależą punkty 1.4, 2.6 i cały Etap 1.

- [ ] **0.2 (K) Odszukaj plik cech użyty do finalnego treningu** — plik z pięcioma kolumnami cech + `is_dyslexic`

  Zbiór, który dał wagi `8b730cd`, nigdy nie trafił do repozytorium. Jeśli nie masz go
  na dysku — wersją pracy musi być `bd60e47`, bo tylko ona jest odtwarzalna.
  Sprawdź kopie zapasowe, zanim zdecydujesz w 0.1.

---

## ETAP 1 — Napraw dane i kod

Wszystkie liczby w rozdziale 5 pochodzą z tego etapu. Zrób go przed jakąkolwiek korektą
tekstu, inaczej będziesz poprawiać dwa razy.

- [ ] **1.1 (K) Przywróć plik cech z etykietami do repozytorium**
  `git checkout 859dafc^ -- wyniki_grupowe_etdd70_meaningful_text.csv`
  Bez tego pliku rozdział 5 jest nieodtwarzalny z definicji. To załącznik do pracy, nie plik roboczy.

- [ ] **1.2 (K) Dopisz liczenie macierzy pomyłek do trenera** — `model_trainer.py`, po linii 127
  Dodaj `cross_val_predict` i `confusion_matrix`, wypisz TP/FN/FP/TN. Obecnie skrypt drukuje
  wyłącznie średnie, więc Tab. 5.1 nie ma źródła w kodzie. Przy okazji dopisz `np.std` wag
  między foldami — przyda się w 2.9.

- [ ] **1.3 (K) Uruchom trening i zapisz wyniki na bok**
  `python model_trainer.py --input <plik z 1.1>`
  Zanotuj dokładność, czułość i swoistość **razem z odchyleniami** oraz macierz z 1.2.
  Wartość odniesienia z recenzji: **75,7% / 73,7% / 77,7%**.

- [ ] **1.4 (K) Zsynchronizuj `model_config.json` z zestawem awaryjnym** — `analysis_core.py`:451–460
  Zestaw awaryjny w kodzie musi być kopią pliku konfiguracyjnego. Synchronizacja jest ręczna.

- [ ] **1.5 (W) Popraw trzy etykiety jednostek w raporcie** — `analysis_individual.py`:181, 189, 190
  Linia 181: „Częstotliwość próbkowania: 6.67 ms" → „Okres próbkowania" (albo przelicz na Hz).
  Linie 189–190: `px` → `DVA`, bo obie wartości przechodzą przez `px_to_dva`.

- [ ] **1.6 (K) Wygeneruj Rys. 4.19 od nowa** — praca, s. 46
  Obecny zrzut pokazuje cechy w pikselach standaryzowane względem statystyk w stopniach —
  z-score wychodzi +684 i +121, stąd `WYNIK MODELU: 0.000`. To artefakt jednostek, nie ocena
  ryzyka. Użyj nagrania z identyfikatorem pseudonimowym (patrz 7.7).

- [ ] **1.7 (W) Rozstrzygnij, co pokazuje Rys. 4.1** — praca, s. 34
  Podpis mówi „Zadanie 1: Czytanie tekstu", a bodziec to sześciowierszowa odprawa misji
  zakończona „Naciśnij ENTER, aby kontynuować". Albo podmień rysunek, albo napisz wprost,
  że bodźcem na stanowisku jest tekst fabularny — i skonfrontuj to z Rys. 4.2.

---

## ETAP 2 — Poprawki krytyczne w tekście

Bez tych jedenastu punktów praca zawiera twierdzenia nieprawdziwe albo nieweryfikowalne.
Wszystkie są redakcyjne — żaden nie wymaga powtórzenia badań.

- [ ] **2.1 (K) Przepisz Tab. 5.1** — praca, s. 47, §5.1.1

  | wariant obliczeń | TP | FN | FP | TN |
  |---|---|---|---|---|
  | out-of-fold, `StratifiedKFold(7)` | 26 | 9 | 8 | 27 |
  | wzór (3.2), resubstytucja | 27 | 8 | 7 | 28 |
  | model HEAD, resubstytucja | 27 | 8 | 6 | 29 |
  | kolumna `score` w zachowanym CSV | 26 | 9 | 6 | 29 |
  | **praca, Tab. 5.1** | **28** | **7** | **7** | **28** |

  Macierz 28/7/7/28 nie wychodzi z żadnego wariantu. Powtarzany sprawdzian z 5 powtórzeniami
  daje **35 macierzy**, a każdy uczestnik jest klasyfikowany 5 razy — jedna macierz na 70
  przypadków dla tej procedury nie istnieje. Zastąp ją średnimi ± odchylenie z 1.3.

- [ ] **2.2 (K) Popraw 80,0% — miejsce 1 z 5** — s. 47–48, §5.1.1, trzy wypunktowania
- [ ] **2.3 (K) Popraw 80,0% — miejsce 2 z 5** — s. 1, Streszczenie (dwie liczby i dwa ułamki „28 z 35")
- [ ] **2.4 (K) Popraw 80,0% — miejsce 3 z 5** — s. 49, §5.3, akapit wprowadzający
- [ ] **2.5 (K) Popraw 80,0% — miejsca 4 i 5 z 5** — s. 52 §6.2 · s. 2 Abstract

- [ ] **2.6 (K) Zaktualizuj równanie (3.2) i opisy współczynników** — s. 28
  Wartości w nawiasach przy każdej cesze (1,71 / 1,04 / −0,33 / 0,76 / −0,16) też są częścią
  wzoru. Sprawdź również §9.3 README, który podaje wagi HEAD.

- [ ] **2.7 (K) Popraw interpretację cechy x₃** — s. 28, §3.4.4, trzecie wypunktowanie

  | cecha | kontrola | dyslektycy | Cohen d | AUC | β | odch. β |
  |---|---|---|---|---|---|---|
  | `fix_reg_duration` (x₁) | 296,4 ms | 378,9 ms | +1,32 | 0,827 | 1,707 | 0,605 |
  | `fix_prog_duration` (x₂) | 362,8 ms | 483,4 ms | +1,34 | 0,845 | 1,041 | 0,337 |
  | **`fix_reg_std` (x₃)** | 205,9 ms | **330,6 ms** | **+1,25** | **0,867** | −0,329 | **0,892** |
  | `sac_prog_y_stab` (x₄) | 0,347° | 0,388° | +0,34 | 0,578 | 0,764 | 0,218 |
  | `sac_prog_dist_avg` (x₅) | 1,909° | 1,564° | −0,87 | 0,268 | −0,165 | 0,230 |

  Praca pisze, że ujemny współczynnik oznacza „mniejszą plastyczność i nadmierną monotonię".
  W danych jest odwrotnie: `fix_reg_std` jest u dyslektyków **wyższe o 61%**, przy czym to
  najsilniejszy pojedynczy dyskryminator w zestawie. Ujemny znak to efekt supresora przy
  korelacji 0,86 z x₁.

- [ ] **2.8 (K) Osłab interpretację cechy x₅** — s. 29, §3.4.4, piąte wypunktowanie
  Kierunek zgodny z [11], ale współczynnik nieodróżnialny od zera: odchylenie 0,230 przy
  średniej −0,165, znak dodatni w 20% foldów.

- [ ] **2.9 (K) Dopisz akapit o kolinearności do §5.3** — s. 49, nowy podrozdział przed 5.3.1
  Macierz korelacji (r(x₁,x₃) = 0,86; r(x₂,x₅) = −0,62) i rozrzut wag między foldami.
  `LogisticRegression(C=np.inf)` celowo wyłącza regularyzację — to główne źródło niestabilności.
  **Ten akapit wzmacnia pracę.**

- [ ] **2.10 (K) Przetłumacz Abstract od nowa** — s. 2
  Wersja polska ma trzy zastrzeżenia, których angielska nie ma: walidacja na ETDD70 a nie na
  stanowisku, wyniki charakteryzują model a nie platformę, pełna podatność na symulację.
  Abstract kończy się na „sets the right direction".

- [ ] **2.11 (K) Przepisz trzeci punkt §5.3.1** — s. 49
  Fałszywie ujemne pochodzą z ETDD70 przy **250 Hz**, nie z Gazepointa 150 Hz. I prędkości
  sakad nie da się policzyć **przy żadnej częstotliwości**, bo są rekonstruowane jako wektory
  z `duration_samples = 0` — tak jak §3.4.2 poprawnie opisuje.

---

## ETAP 3 — Poprawki ważne

- [ ] **3.1 (W) Dopisz porównanie z wynikiem autorów ETDD70** — s. 47 §5.1 albo s. 52 §6.2
  Raportują ~**90%** na tych samych danych. Porównanie działa na Twoją korzyść: Twój model
  ma pięć cech i jest interpretowalny.
- [ ] **3.2 (W) Przeformułuj wniosek z testów odpornościowych** — s. 48, §5.2.2
  Propozycja: „wszyscy uczestnicy symulujący objawy zostali zaklasyfikowani do grupy wysokiego
  ryzyka (P od 0,71 do 0,95), przy wynikach kontrolnych 0,06–0,32".
- [ ] **3.3 (W) Dopisz zastrzeżenie o geometrii do §5.2** — s. 48
  Testy na 1920×1080, normy dla 1680×1050 / 47,4 cm / 60 cm. Pionowe DVA zawyżone o 11,1%
  przy cesze x₄ z wagą +0,76 — błąd przesuwa wynik **w stronę wysokiego ryzyka**.
- [ ] **3.4 (W) Doprecyzuj, czyje dane opisuje §5.3.4** — s. 50
  Żadne dziecko nie było badane na zbudowanym stanowisku.
- [ ] **3.5 (W) Osłab twierdzenie o stabilności akwizycji** — s. 51, §6.1
  „stabilnej rejestracji" nie jest poparte żadną miarą — albo podaj liczby, albo skreśl słowo.
- [ ] **3.6 (W) Uzupełnij listę rejestrowanych parametrów** — s. 30, §4.2.1
  Brak `LPOGX/Y/V` i `RPOGX/Y/V` — a **cały argument o obuocznej odporności I2MC** opiera się
  na tych kanałach.
- [ ] **3.7 (W) Uzupełnij opis formatu danych surowych** — s. 25, §3.3.3
- [ ] **3.8 (W) Popraw opis mechanizmu awaryjnego** — s. 35, §4.4.7
  „lub błędu jego odczytu" — kod sprawdza tylko `os.path.exists()`, brak `try/except`.
- [ ] **3.9 (W) Opisz rzeczywisty przebieg etykietowania** — s. 35–36, §4.4.8
  Repozytorium ma `dodaj_etykiety.py`, a §5.1 mówi, że etykiety wzięto z pliku.
- [ ] **3.10 (W) Dopisz `dodaj_etykiety.py` do wykazu plików** — s. 19, §3.1.1
- [ ] **3.11 (W) Popraw cztery nazwy plików na Rys. 3.5** — s. 21
  `weryfikacje_dane_surowe.csv` → `weryfikacja_dane_surowe.csv` ·
  `weryfikacje_zdarzenia.csv` → `weryfikacja_zdarzenia.csv` ·
  `gra_dane_zdarzenia.csv` → `gra_zdarzenia.csv` (także §3.3.3 na s. 25) ·
  `tlo_kokpitu.jpg` → `tlo_kokpit.jpg`
- [ ] **3.12 (W) Popraw asymetryczną niepewność DVA** — s. 28, §3.4.3
  „±17%" → „od −14% do +20%" (D = 50 cm: +20,0%; D = 70 cm: −14,3%).
- [ ] **3.13 (W) Uzupełnij opis opóźnienia startu rejestracji** — s. 22, §3.2.2
  Literówka „wystymowane" → „oszacowane"; brak metody pomiaru; brak omówienia skutku —
  pierwsze ~100 ms czytania nie trafia do zapisu i nie jest kompensowane.
- [ ] **3.14 (W) Dopisz ograniczenie pytania weryfikacyjnego** — s. 23, §3.2.2
  Poprawna odpowiedź **zaszyta na stałe jako „A"** (`experiment_module.py:178`).
- [ ] **3.15 (W) Rozdziel dwa znaczenia „walidacji zewnętrznej"** — s. 6 §1.2 · s. 49 §5.3
- [ ] **3.16 (W) Doprecyzuj realizację celu „pomiary testowe"** — s. 6 §1.2 · s. 51 §6.1
- [ ] **3.17 (W) Ujednolić opis liczby 31 868** — s. 6 §1.1 · s. 8 §2.1
  „z dostosowaniem warunków" ≠ „uczniowie z dysleksją".
- [ ] **3.18 (W) Skomentuj rozbieżność 5–10% wobec 12%** — s. 6, §1.1
- [ ] **3.19 (D) Popraw liczbę parametrów filtra 1€** — s. 24, §3.3.1 — ma trzy, nie dwa
- [ ] **3.20 (D) Dopisz szwedzkie pochodzenie grupy z [11]** — s. 9, §2.4

---

## ETAP 4 — Bibliografia

- [ ] **4.1 (W) [2] CKE — tytuł, rok, data dostępu** — s. 53
  Tytuł i rok mówią 2023, treść dotyczy sesji 2025, URL wskazuje `sprawozdanie_matura_2025_polski.pdf`.
- [ ] **4.2 (D) [33] — rozsypany znak euro** — „1 C filter" → „1€ Filter"
- [ ] **4.3 (W) [6] i [7] — zły typ wpisu** — baterie diagnostyczne opisane jako artykuły w czasopiśmie
- [ ] **4.4 (D) [9] — niepełny tytuł** — *Eye Tracking Methodology: Theory and Practice*
- [ ] **4.5 (D) [27] — czterej autorzy zamiast „i in.", pełna nazwa czasopisma**
- [ ] **4.6 (W) [34] — sprawdź, czy to DOI wersji czy koncepcyjny** (rekord `13332134`)
- [ ] **4.7 (D) [3] ICD-11 — data dostępu i aktualność wydania**
- [ ] **4.8 (D) [29]–[32] — ujednolić format i kolejność dat**
- [ ] **4.9 (D) Popraw atrybucję ETDD70** — Masaryk **i** Duisburg-Essen

---

## ETAP 5 — Powołania i brakujące źródła

Trzy pierwsze punkty to weryfikacja w oryginałach — nie udało mi się do nich dotrzeć
przez blokadę sieci.

- [ ] **5.1 (W) Zweryfikuj czułość i swoistość z [11]** — s. 9, §2.4
  Dokładność 95,6% potwierdzona; pary **95,5% / 95,7%** nie.
- [ ] **5.2 (W) Zweryfikuj opis aparatury z [11]** — Ober-2, 100 Hz, podparcie brody i czoła
- [ ] **5.3 (W) Zweryfikuj metodę rekonstrukcji sakad w [35]** — s. 47, §5.1
- [ ] **5.4 (D) Przenieś przypisy przy czasie trwania sakad** — s. 11, §2.7.2
  [20, 21, 22] dotyczą tłumienia sakadowego, nie czasu trwania.
- [ ] **5.5 (D) Zawęź zakres czasu fiksacji do czytania** — s. 11, §2.7.1
  Rayner (2009): ~225 ms dla czytania, ~275 ms dla przeszukiwania, ~330 ms dla percepcji scen.
- [ ] **5.6 (W) Dodaj źródło dla Varjo XR-4** — s. 52, §6.3 — podane bez żadnego źródła
- [ ] **5.7 (W) Dodaj źródła do §2.8** — s. 12 — cały podrozdział bez przypisów; także §2.7.3
- [ ] **5.8 (W) Dodaj źródło dla przejrzystości ortografii** — s. 50, §5.3.5
- [ ] **5.9 (D) Osłab twierdzenie o skuteczności grywalizacji** — s. 22, §3.2.1
- [ ] **5.10 (D) Skonsoliduj powtórzone przypisy** — [11] 7×, [27] 5×
- [ ] **5.11 (D) Rozważ DSM-5 (§2.1) i TRIPOD (rozdz. 5)**

---

## ETAP 6 — Korekta redakcyjna

Rób to na końcu — wcześniejsze etapy i tak przepiszą część tych zdań.

- [ ] **6.1 (D) s. 10 — brakujące spacje po odsyłaczach** (§2.5, cztery miejsca)
- [ ] **6.2 (D) s. 10 — `VOCR` → `VCR`; nawias przy „czerwonych oczu"** (§2.6)
- [ ] **6.3 (D) s. 12 — brak kropki po numerze tabeli** (§2.8)
- [ ] **6.4 (D) s. 14 — rozbieżny opis dokładności EyeLink** (§2.9 wobec Tab. 2.2)
- [ ] **6.5 (D) s. 16–21 — „Interface" → „Interfejs"** (Rys. 3.1–3.5 i podpis 3.4)
- [ ] **6.6 (D) s. 22–23 — trzy usterki w §3.2.2** (powtórzone „Akwizycja:", „wystymowane", „do późniejszej nałożenia")
- [ ] **6.7 (D) s. 26 — „posród" → „pośród"** (§3.4.2); rozbij pięciowierszowe zdanie
- [ ] **6.8 (D) s. 31–33 — trzy usterki w rozdziale 4** (§4.3.2, §4.4.3, §4.4.4)
- [ ] **6.9 (D) s. 47 — trzy usterki w akapicie §5.1** (sklejone zdania, brak nawiasu, podwójna kropka)
- [ ] **6.10 (D) s. 48–50 — interpunkcja** (§5.2, §5.3, §5.3.3)
- [ ] **6.11 (D) s. 51–52 — trzy usterki w rozdziale 6** („–od", „stanowiłyby", „bądź mieszanej")
- [ ] **6.12 (D) Całość — ujednolić zapis nazwy algorytmu I2MC**

---

## ETAP 7 — Kod (opcjonalnie przed obroną)

Punkty 7.1–7.3 warto zrobić, bo dotyczą poprawności wyniku diagnostycznego.

- [ ] **7.1 (W) R1 — ścieżka konfiguracji względem pliku, nie CWD** — `analysis_core.py`:429
  `config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_config.json")`
- [ ] **7.2 (W) R2 — sparametryzuj geometrię ekranu** — `analysis_core.py`:9–12, `analysis_individual.py`:28–31
  I2MC przyjmuje `scrSz` i `disttoscreen` i sam zwraca statystyki w stopniach — własne
  `px_to_dva` jest w dużej mierze duplikatem.
- [ ] **7.3 (W) R3 — obsłuż uszkodzony plik konfiguracyjny** — `analysis_core.py`:432–437
  W analizie grupowej uczestnik **wypada z raportu bez ostrzeżenia**.
- [ ] **7.4 (D) R4 — ujednolić walidację próbek w obu potokach**
  Potok grupowy nie ma górnego ograniczenia zakresu — przeczy §5.1 o identyczności potoku.
- [ ] **7.5 (D) R6 — dopisz zdanie o modelu uśrednionym** — §3.4.4 albo §5.1
- [ ] **7.6 (D) R7 — ogranicz wzorzec plików do zadania T4** — `analysis_group.py`:148
- [ ] **7.7 (W) R9 — usuń dane osobowe z rysunków** — s. 34 i s. 46
  `.../dane_z_badan/Jerzy_2026-04-14_00-19-07/` przeczy deklaracji z §3.3.4.
- [ ] **7.8 (D) R10 — drobne porządki w kodzie** (`gazepoint.py`:42, `analysis_core.py`:132, `analysis_group.py`:155, `tkinter_module.py`:174)

---

## ETAP 8 — Weryfikacja końcowa

- [ ] **8.1 (K) Uruchom skrypt weryfikacyjny** — `python recenzja/weryfikacja_wynikow.py`
  Jeśli coś się nie zgadza, poprawiaj tekst, nie skrypt.
- [ ] **8.2 (K) Przeszukaj pracę pod kątem starych liczb** — `80,0` · `28 z 35` · `1,707` · `0,272` · `±17`
  To jest ten moment, w którym wychodzi szóste wystąpienie, o którym zapomniałeś.
- [ ] **8.3 (W) Sprawdź spis rysunków i tabel oraz odwołania w tekście**
- [ ] **8.4 (K) Przeczytaj oba streszczenia obok siebie** — zdanie po zdaniu
- [ ] **8.5 (W) Zacommituj i otaguj wersję odpowiadającą pracy** — `git tag praca-v1`

---

**Podsumowanie:** 85 punktów — 21 krytycznych, 35 ważnych, 29 drobnych.
Etapy 0–2 i 8 to minimum przed obroną: jeden–dwa dni pracy redakcyjnej plus jedno
uruchomienie skryptu treningowego.
