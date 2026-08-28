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
            '<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />',
            # Ważne: Domyślnie WYŁĄCZAM wysyłanie danych, żeby nie zapychać bufora
            '<SET ID="ENABLE_SEND_DATA" STATE="0" />' 
        ]
        
        # Definicja kolumn CSV
        self.csv_fields = [
            'PC_TIME',   
            'TIME',      
            'TIME_TICK', 
            'BPOGX', 
            'BPOGY', 
            'BPOGV'
        ]

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(2) # Timeout dla operacji blokujących
            
            # Wysyłam konfigurację wstępną
            for cmd in self.init_commands:
                self._send_command(cmd)
                
            print("[INFO] Pomyślnie połączono z Gazepoint Control.")
        except ConnectionRefusedError:
            print("[BŁĄD] Nie można połączyć się z Gazepoint Control.")
            raise

    def _send_command(self, command):
        if self.sock:
            try:
                self.sock.sendall(f"{command}\r\n".encode())
            except OSError:
                pass

    def _flush_socket(self):
        # Opróżnia bufor gniazda ze starych danych (np. z kalibracji).
        # Używa trybu nieblokującego, aby wczytać wszystko co zalega, aż do pustego bufora.
        if not self.sock: return
        
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

    def calibrate(self):
        print("[INFO] Uruchamianie kalibracji systemowej...")
        self._send_command('<SET ID="CALIBRATE_TYPE" VALUE="9" />')
        self._send_command('<SET ID="CALIBRATE_SHOW" STATE="1" />')
        self._send_command('<SET ID="CALIBRATE_START" STATE="1" />')
        print("[INFO] Oczekiwanie na zakończenie kalibracji przez Gazepoint...")
        # Tutaj teoretycznie można by poczekać na ID="CALIBRATE_RESULT"

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