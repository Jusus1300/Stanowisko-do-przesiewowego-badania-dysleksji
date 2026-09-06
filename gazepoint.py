import socket
import xml.etree.ElementTree as ET
import csv
import time
import threading
import experiment_config

from OneEuroFilter import OneEuroFilter

class GazeTracker:
    def __init__(self, host='127.0.0.1', port=4242):
        self.host = host
        self.port = port
        self.sock = None
        
        # Pliki
        self.csv_writer = None
        self.csv_file = None
        self.event_log_file = None
        self.event_writer = None
        
        # Flagi stanu
        self.is_logging = False
        self.logging_thread = None
        
        # Dane Live Preview
        self.latest_gaze_data = {'x': 0.5, 'y': 0.5, 'valid': False}
        self.gaze_data_lock = threading.Lock()
        
        # Synchronizacja Czasu
        self.time_anchor = None 

        # Odbior odpowiedzi na komendy sterujace. _rx_buffer przechowuje
        # nadmiarowe dane doczytane z gniazda przy oczekiwaniu na ACK,
        # a _ack_supported zapamietuje, czy ta wersja Gazepoint Control
        # w ogole potwierdza polecenia (None = jeszcze nie wiadomo).
        self._rx_buffer = ""
        self._ack_supported = None

        # Filtrowanie
        filter_config = {
            'freq': 150,
            'mincutoff': experiment_config.ONE_EURO_MIN_CUTOFF,
            'beta': experiment_config.ONE_EURO_BETA,
            'dcutoff': 1.0
        }
        self.x_filter = OneEuroFilter(**filter_config)
        self.y_filter = OneEuroFilter(**filter_config)

        # Komendy konfiguracyjne.
        self.init_commands = [
            '<SET ID="ENABLE_SEND_TIME" STATE="1" />',
            '<SET ID="ENABLE_SEND_TIME_TICK" STATE="1" />',
            # Punkt spojrzenia osobno dla każdego oka. Bez tych dwóch komend
            # GP3 wysyła wyłącznie BPOG, czyli punkt już uśredniony przez
            # okulograf - a wtedy I2MC nie ma dwóch niezależnych sygnałów do
            # grupowania i deklarowana odporność algorytmu na szum nie jest
            # osiągana (patrz analiza_obuoczna_i2mc.md).
            '<SET ID="ENABLE_SEND_POG_LEFT" STATE="1" />',
            '<SET ID="ENABLE_SEND_POG_RIGHT" STATE="1" />',
            # BPOG zostaje: służy do podglądu na żywo i jako zapas dla nagrań,
            # w których któreś z oczu nie było widoczne.
            '<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />',
            # Ważne: Domyślnie WYŁĄCZAM wysyłanie danych, żeby nie zapychać bufora
            '<SET ID="ENABLE_SEND_DATA" STATE="0" />'
        ]

        # Definicja kolumn CSV. LPOG*/RPOG* to punkt spojrzenia oka lewego
        # i prawego, LPOGV/RPOGV - flagi poprawności każdego z nich (potok
        # analizy odrzuca próbkę na jednym oku nie unieważniając drugiego).
        self.csv_fields = [
            'PC_TIME',
            'TIME',
            'TIME_TICK',
            'LPOGX',
            'LPOGY',
            'LPOGV',
            'RPOGX',
            'RPOGY',
            'RPOGV',
            'BPOGX',
            'BPOGY',
            'BPOGV'
        ]

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(2) # Timeout dla operacji blokujących
            
            # Wysyłam konfigurację wstępną i sprawdzam, czy została przyjęta -
            # odrzucone ENABLE_SEND_POG_BEST oznaczałoby puste kolumny BPOGX/BPOGY
            # w nagraniu, co bez tej kontroli wyszłoby dopiero na etapie analizy.
            # Tak samo odrzucone ENABLE_SEND_POG_LEFT/RIGHT dałoby puste kolumny
            # LPOG*/RPOG*, a potok analizy zszedłby po cichu do trybu jednoocznego
            # na BPOG - stąd komunikat o błędzie już na etapie łączenia.
            for cmd in self.init_commands:
                if self._send_command(cmd, expect_id=self._command_id(cmd)) is False:
                    print(f"[BLAD] Gazepoint odrzucil komende startowa: {cmd}")

            print("[INFO] Pomyślnie połączono z Gazepoint Control.")
        except ConnectionRefusedError:
            print("[BŁĄD] Nie można połączyć się z Gazepoint Control.")
            raise

    @staticmethod
    def _command_id(command):
        # Wyciaga wartosc atrybutu ID z komendy, zeby dopasowac do niej ACK.
        try:
            return ET.fromstring(command).get('ID')
        except ET.ParseError:
            return None

    @staticmethod
    def _ack_verdict(line, expect_id):
        # True dla ACK, False dla NACK, None gdy linia dotyczy czegos innego
        # (np. rekordu danych, ktory zalega w buforze).
        line = line.strip()
        if not (line.startswith('<ACK') or line.startswith('<NACK')):
            return None
        try:
            root = ET.fromstring(line)
        except ET.ParseError:
            return None
        if root.get('ID') != expect_id:
            return None
        return root.tag == 'ACK'

    def _await_ack(self, expect_id, timeout):
        # Czyta z gniazda az do ACK/NACK o pasujacym ID albo do uplywu czasu.
        # Nadmiarowe linie zostaja w _rx_buffer, zeby nic nie zginelo.
        deadline = time.monotonic() + timeout
        while True:
            while '\r\n' in self._rx_buffer:
                line, self._rx_buffer = self._rx_buffer.split('\r\n', 1)
                verdict = self._ack_verdict(line, expect_id)
                if verdict is not None:
                    return verdict

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                self.sock.settimeout(remaining)
                chunk = self.sock.recv(4096)
            except (socket.timeout, OSError):
                return None
            finally:
                try:
                    self.sock.settimeout(2)
                except OSError:
                    pass
            if not chunk:
                return None
            self._rx_buffer += chunk.decode('utf-8', errors='ignore')

    def _send_command(self, command, expect_id=None, timeout=1.0):
        # Zwraca True (ACK), False (NACK) albo None, gdy potwierdzenia nie
        # sprawdzano lub serwer nie odpowiedzial. Nigdy nie rzuca wyjatkiem -
        # brak potwierdzenia degraduje sie do dawnego zachowania "wyslij i idz
        # dalej", ale zostaje odnotowany w konsoli.
        if not self.sock:
            return None
        try:
            self.sock.sendall(f"{command}\r\n".encode())
        except OSError as e:
            print(f"[BLAD] Nie udalo sie wyslac komendy {command}: {e}")
            return None

        if expect_id is None or self._ack_supported is False:
            return None

        verdict = self._await_ack(expect_id, timeout)
        if verdict is None:
            if self._ack_supported is None:
                # Pierwsza komenda bez odpowiedzi: przyjmuje, ze ta wersja
                # Gazepoint Control nie potwierdza polecen, i przestaje na nie
                # czekac, zeby nie mnozyc timeoutow przy kazdej kolejnej.
                self._ack_supported = False
                print("[WARN] Gazepoint Control nie odpowiada na komendy SET - "
                      "poprawnosc ustawien nie bedzie weryfikowana.")
        else:
            self._ack_supported = True
        return verdict

    def _flush_socket(self):
        # Opróżnia bufor gniazda ze starych danych (np. z kalibracji).
        # Używa trybu nieblokującego, aby wczytać wszystko co zalega, aż do pustego bufora.
        if not self.sock: return

        self._rx_buffer = ""

        try:
            self.sock.setblocking(False) # Tryb nieblokujący
            while True:
                data = self.sock.recv(4096)
                if not data: break
        except BlockingIOError:
            # To jest oczekiwane - oznacza, że bufor jest pusty
            pass
        except OSError:
            pass
        finally:
            self.sock.setblocking(True) # Przywracam tryb blokujący

    def calibration_grid(self):
        # Siatka 3x3 (9 punktów) we współrzędnych znormalizowanych, budowana
        # z marginesu w experiment_config. Kolejność wierszami, od lewej
        # górnej do prawej dolnej - Gazepoint kalibruje w kolejności dodania.
        m = experiment_config.CALIBRATION_MARGIN
        coords = (m, 0.5, 1.0 - m)
        return [(x, y) for y in coords for x in coords]

    def calibrate(self):
        # Open Gaze API nie ma komendy ustawiającej "typ" kalibracji - liczbę
        # i rozmieszczenie punktów definiuje się czyszcząc listę punktów
        # (CALIBRATE_CLEAR), a następnie dodając je pojedynczo
        # (CALIBRATE_ADDPOINT). Wcześniejsze CALIBRATE_TYPE nie istnieje
        # w protokole: serwer odrzucał je, a ponieważ kod nie czytał
        # odpowiedzi, w praktyce działała domyślna kalibracja z Gazepoint
        # Control, nie 9-punktowa.
        points = self.calibration_grid()
        print(f"[INFO] Konfiguracja kalibracji {len(points)}-punktowej...")

        if self._send_command('<SET ID="CALIBRATE_CLEAR" STATE="1" />',
                              expect_id="CALIBRATE_CLEAR") is False:
            print("[BLAD] Gazepoint odrzucil wyczyszczenie listy punktow "
                  "kalibracyjnych - do siatki moga dojsc punkty domyslne.")

        accepted = 0
        for i, (x, y) in enumerate(points, start=1):
            verdict = self._send_command(
                f'<SET ID="CALIBRATE_ADDPOINT" X="{x:.4f}" Y="{y:.4f}" />',
                expect_id="CALIBRATE_ADDPOINT"
            )
            if verdict is False:
                print(f"[BLAD] Gazepoint odrzucil punkt {i} ({x:.2f}, {y:.2f}).")
            elif verdict is True:
                accepted += 1

        if self._ack_supported is False:
            print(f"[WARN] Gazepoint nie potwierdza komend - nie moge zweryfikowac, "
                  f"czy przyjal {len(points)} punktow. Sprawdz liczbe punktow "
                  f"w oknie Gazepoint Control.")
        elif accepted == len(points):
            print(f"[INFO] Gazepoint przyjal {accepted}/{len(points)} punktow kalibracyjnych.")
        else:
            print(f"[BLAD] Gazepoint przyjal tylko {accepted}/{len(points)} punktow - "
                  f"kalibracja NIE jest {len(points)}-punktowa.")

        self._send_command('<SET ID="CALIBRATE_SHOW" STATE="1" />',
                           expect_id="CALIBRATE_SHOW")
        self._send_command('<SET ID="CALIBRATE_START" STATE="1" />',
                           expect_id="CALIBRATE_START")
        print("[INFO] Oczekiwanie na zakończenie kalibracji przez Gazepoint...")

    def start_logging(self, data_filename, event_filename, save_events):
        # 1. Najpierw wyrzucam śmieci z bufora
        self._flush_socket()
        
        # 2. Otwieram pliki
        self.csv_file = open(data_filename, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.csv_fields)
        self.csv_writer.writeheader()
        
        if(save_events==True):
            self.event_log_file = open(event_filename, 'w', newline='', encoding='utf-8')
            self.event_writer = csv.writer(self.event_log_file)
            self.event_writer.writerow(['Timestamp', 'EventMessage'])
        
        self.time_anchor = None
        self.is_logging = True
        
        # 3. Włączam przesył danych w Gazepoint
        self._send_command('<SET ID="ENABLE_SEND_DATA" STATE="1" />')
        
        # 4. Uruchamiam wątek odbierający
        self.logging_thread = threading.Thread(target=self._logging_loop, daemon=True)
        self.logging_thread.start()

    def log_event(self, message):
        if self.event_writer:
            timestamp = time.time()
            self.event_writer.writerow([timestamp, message])
            self.event_log_file.flush() 

    def stop_logging(self):
        # 1. Najpierw zatrzymuję pętlę w Pythonie
        self.is_logging = False
        
        # 2. Wysyłam komendę STOP do Gazepoint, żeby przestał wysyłać dane do bufora
        self._send_command('<SET ID="ENABLE_SEND_DATA" STATE="0" />')
        
        if self.logging_thread and self.logging_thread.is_alive():
            self.logging_thread.join(timeout=1.0)
        
        if self.csv_file: 
            self.csv_file.close()
            self.csv_file = None
        if self.event_log_file: 
            self.event_log_file.close()
            self.event_log_file = None

    def _parse_and_process_gaze_data(self, xml_str, recv_timestamp):
        try:
            xml_str = xml_str.strip()
            if not xml_str.startswith('<REC'): return
            
            root = ET.fromstring(xml_str)
            if root.tag == 'REC':
                
                tracker_time_str = root.get('TIME')
                if tracker_time_str is None: return
                tracker_time = float(tracker_time_str)

                # Logika synchronizacji czasu
                if self.time_anchor is None:
                    self.time_anchor = (recv_timestamp, tracker_time)
                
                anchor_pc, anchor_tracker = self.time_anchor
                calculated_pc_time = anchor_pc + (tracker_time - anchor_tracker)

                if self.csv_writer:
                    data_dict = {}
                    for field in self.csv_fields:
                        if field == 'PC_TIME':
                            data_dict[field] = f"{calculated_pc_time:.4f}"
                        else:
                            val = root.get(field)
                            data_dict[field] = val if val is not None else ''
                    
                    self.csv_writer.writerow(data_dict)

                # Live Preview
                bpog_x_str = root.get('BPOGX')
                bpog_y_str = root.get('BPOGY')
                
                if bpog_x_str is not None and bpog_y_str is not None:
                    bpog_x = float(bpog_x_str)
                    bpog_y = float(bpog_y_str)
                    
                    smooth_x = self.x_filter(bpog_x, tracker_time)
                    smooth_y = self.y_filter(bpog_y, tracker_time)
                    is_bpog_valid = root.get('BPOGV') == '1'

                    with self.gaze_data_lock:
                        self.latest_gaze_data['x'] = smooth_x
                        self.latest_gaze_data['y'] = smooth_y
                        self.latest_gaze_data['valid'] = is_bpog_valid
                else:
                    with self.gaze_data_lock:
                        self.latest_gaze_data['valid'] = False
                        
        except (ET.ParseError, ValueError, TypeError, AttributeError):
            pass

    def get_latest_gaze_data(self):
        with self.gaze_data_lock:
            return self.latest_gaze_data.copy()

    def _logging_loop(self):
        if not self.sock: return
        buffer = ""
        while self.is_logging:
            try:
                data = self.sock.recv(4096).decode('utf-8', errors='ignore')
                if not data: break
                
                recv_timestamp = time.time()
                
                buffer += data
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    self._parse_and_process_gaze_data(line, recv_timestamp)
                    
            except (socket.timeout, ConnectionAbortedError, OSError):
                break

    def close(self):
        if self.sock:
            self._send_command('<SET ID="ENABLE_SEND_DATA" STATE="0" />')
            self.sock.close()
            self.sock = None
        self.stop_logging()