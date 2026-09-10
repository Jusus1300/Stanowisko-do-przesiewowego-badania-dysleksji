# Klient Open Gaze API (Gazepoint GP3): kalibracja, zapis surowych próbek do CSV
# i wygładzony podgląd wzroku na żywo dla zadania z celem.

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
        
        # Pliki wyjściowe
        self.csv_writer = None
        self.csv_file = None
        self.event_log_file = None
        self.event_writer = None
        
        # Stan wątku rejestrującego
        self.is_logging = False
        self.logging_thread = None
        
        # Ostatnia próbka dla podglądu na żywo - czytana z wątku pygame
        self.latest_gaze_data = {'x': 0.5, 'y': 0.5, 'valid': False}
        self.gaze_data_lock = threading.Lock()
        
        # Punkt zaczepienia zegara okulografu do zegara PC
        self.time_anchor = None 

        # Odbiór potwierdzeń komend. W _rx_buffer zostaje to, co doczytaliśmy
        # z gniazda czekając na ACK; _ack_supported = None znaczy "jeszcze nie
        # wiadomo, czy ta wersja Gazepoint Control w ogóle potwierdza polecenia".
        self._rx_buffer = ""
        self._ack_supported = None

        filter_config = {
            'freq': 150,
            'mincutoff': experiment_config.ONE_EURO_MIN_CUTOFF,
            'beta': experiment_config.ONE_EURO_BETA,
            'dcutoff': 1.0
        }
        self.x_filter = OneEuroFilter(**filter_config)
        self.y_filter = OneEuroFilter(**filter_config)

        # Konfiguracja startowa okulografu.
        self.init_commands = [
            '<SET ID="ENABLE_SEND_TIME" STATE="1" />',
            '<SET ID="ENABLE_SEND_TIME_TICK" STATE="1" />',
            # Punkt spojrzenia osobno dla każdego oka - bez tego GP3 wysyła tylko
            # BPOG (już uśredniony) i I2MC nie ma dwóch sygnałów do grupowania.
            '<SET ID="ENABLE_SEND_POG_LEFT" STATE="1" />',
            '<SET ID="ENABLE_SEND_POG_RIGHT" STATE="1" />',
            # BPOG zostaje: podgląd na żywo i zapas, gdy któreś oko przepadnie.
            '<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />',
            # Przesył domyślnie wyłączony, żeby nie zapychać bufora przed startem.
            '<SET ID="ENABLE_SEND_DATA" STATE="0" />'
        ]

        # Kolumny nagrania: LPOG*/RPOG* to oko lewe i prawe, *POGV - flagi
        # poprawności każdego z sygnałów osobno.
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
            self.sock.settimeout(2)  # timeout operacji blokujących
            
            # Sprawdzamy, czy ustawienia zostały przyjęte - odrzucone POG_LEFT/RIGHT
            # dałoby puste kolumny w nagraniu i wyszłoby dopiero przy analizie.
            for cmd in self.init_commands:
                if self._send_command(cmd, expect_id=self._command_id(cmd)) is False:
                    print(f"[BLAD] Gazepoint odrzucil komende startowa: {cmd}")

            print("[INFO] Pomyślnie połączono z Gazepoint Control.")
        except ConnectionRefusedError:
            print("[BŁĄD] Nie można połączyć się z Gazepoint Control.")
            raise

    @staticmethod
    def _command_id(command):
        # Atrybut ID komendy - po nim dopasowujemy ACK.
        try:
            return ET.fromstring(command).get('ID')
        except ET.ParseError:
            return None

    @staticmethod
    def _ack_verdict(line, expect_id):
        # True = ACK, False = NACK, None = linia dotyczy czegoś innego (np. rekordu
        # danych zalegającego w buforze).
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
        # Czyta do skutku albo do upływu czasu. Nadmiarowe linie zostają
        # w _rx_buffer, żeby nic nie zginęło.
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
        # Nigdy nie rzuca wyjątkiem: brak potwierdzenia degraduje się do dawnego
        # "wyślij i idź dalej", ale zostaje odnotowany w konsoli.
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
                # Pierwsza komenda bez odpowiedzi - ta wersja Gazepointa nie
                # potwierdza poleceń, więc przestajemy czekać przy kolejnych.
                self._ack_supported = False
                print("[WARN] Gazepoint Control nie odpowiada na komendy SET - "
                      "poprawnosc ustawien nie bedzie weryfikowana.")
        else:
            self._ack_supported = True
        return verdict

    def _flush_socket(self):
        # Wyrzuca z bufora dane zalegające np. po kalibracji. Tryb nieblokujący,
        # czytamy aż do pustego bufora.
        if not self.sock: return

        self._rx_buffer = ""

        try:
            self.sock.setblocking(False)
            while True:
                data = self.sock.recv(4096)
                if not data: break
        except BlockingIOError:
            pass  # oczekiwane: bufor pusty
        except OSError:
            pass
        finally:
            self.sock.setblocking(True)

    def calibration_grid(self):
        # Siatka 3x3 we współrzędnych znormalizowanych, wierszami od lewego górnego
        # rogu - Gazepoint kalibruje w kolejności dodawania punktów.
        m = experiment_config.CALIBRATION_MARGIN
        coords = (m, 0.5, 1.0 - m)
        return [(x, y) for y in coords for x in coords]

    def calibrate(self):
        # Open Gaze API nie ma komendy ustawiającej "typ" kalibracji - liczbę
        # punktów definiuje się przez CALIBRATE_CLEAR i kolejne CALIBRATE_ADDPOINT.
        # Wcześniejsze CALIBRATE_TYPE nie istnieje w protokole: serwer je odrzucał,
        # a kod nie czytał odpowiedzi, więc działała kalibracja domyślna.
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
        self._flush_socket()  # najpierw śmieci z poprzedniego etapu
        
        self.csv_file = open(data_filename, 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.csv_fields)
        self.csv_writer.writeheader()
        
        if(save_events==True):
            self.event_log_file = open(event_filename, 'w', newline='', encoding='utf-8')
            self.event_writer = csv.writer(self.event_log_file)
            self.event_writer.writerow(['Timestamp', 'EventMessage'])
        
        self.time_anchor = None
        self.is_logging = True
        
        # Przesył włączamy dopiero z gotowym plikiem, wątek odbiera go w tle.
        self._send_command('<SET ID="ENABLE_SEND_DATA" STATE="1" />')
        
        self.logging_thread = threading.Thread(target=self._logging_loop, daemon=True)
        self.logging_thread.start()

    def log_event(self, message):
        if self.event_writer:
            timestamp = time.time()
            self.event_writer.writerow([timestamp, message])
            self.event_log_file.flush() 

    def stop_logging(self):
        # Kolejność ma znaczenie: najpierw pętla w Pythonie, potem cisza po stronie
        # okulografu, na końcu zamknięcie plików.
        self.is_logging = False
        
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

                # Czas okulografu przeliczamy na czas PC względem pierwszej próbki.
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

                # Podgląd na żywo idzie z BPOG i przez filtr 1 Euro - surowy punkt
                # zbyt drga, żeby dało się nim celować.
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
            pass  # uszkodzony rekord pomijamy, nagranie leci dalej

    def get_latest_gaze_data(self):
        with self.gaze_data_lock:
            return self.latest_gaze_data.copy()

    def _logging_loop(self):
        # Wątek odbiorczy: strumień TCP trzeba pociąć po \r\n, bo pakiety nie
        # pokrywają się z rekordami.
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
