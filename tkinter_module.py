import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from screeninfo import get_monitors, ScreenInfoError
import experiment_config as cfg

def _get_center_geometry(window_width, window_height, monitor_index=0):
    # Pozostawione dla pomniejszych okien (np. raportu)
    try:
        monitors = get_monitors()
        if not monitors:
            raise ScreenInfoError("Nie znaleziono monitorów.")
        target_monitor = monitors[monitor_index] if monitor_index < len(monitors) else monitors[0]
        center_x = target_monitor.x + (target_monitor.width - window_width) // 2
        center_y = target_monitor.y + (target_monitor.height - window_height) // 2
        return f'{window_width}x{window_height}+{center_x}+{center_y}'
    except (ScreenInfoError, IndexError):
        root = tk.Tk()
        root.withdraw()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        root.destroy()
        return f'{window_width}x{window_height}+{center_x}+{center_y}'

def _setup_fullscreen_bg(root, monitor_index=0):
    # Ustawia okno na pełny ekran, wczytuje i wyświetla zdjęcie jako tło
    # oraz umieszcza okno na docelowym monitorze.
    # 1. Podstawowa konfiguracja okna
    root.attributes('-fullscreen', True)
    root.configure(bg='black') # Tło awaryjne, jeśli zdjęcie się nie załaduje

    try:
        monitors = get_monitors()
        if monitors:
            target_monitor = monitors[monitor_index] if monitor_index < len(monitors) else monitors[0]
            # Ustaw pozycję startową na wybranym monitorze
            root.geometry(f"+{target_monitor.x}+{target_monitor.y}")
            # Pobierz rozdzielczość monitora
            screen_width = target_monitor.width
            screen_height = target_monitor.height
        else:
            raise ScreenInfoError("Nie znaleziono monitorów.")
    except Exception:
        # W razie błędu pobierania informacji o monitorach, użyj domyślnych
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

    # 2. Wczytanie i obsługa zdjęcia tła
    try:
        # Ścieżka do zdjęcia tła z konfiguracji
        image_path = cfg.BACKGROUND_IMG
        
        # Otwórz zdjęcie za pomocą PIL
        pil_image = Image.open(image_path)
        
        # Przeskaluj zdjęcie do rozdzielczości ekranu
        pil_image = pil_image.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
        
        # Konwersja na format zrozumiały dla Tkintera
        root.background_image = ImageTk.PhotoImage(pil_image)
        
        # Utwórz Label, który będzie trzymał zdjęcie i wypełni całe okno
        bg_label = tk.Label(root, image=root.background_image)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Upewnij się, że etykieta tła jest pod spodem innych elementów
        bg_label.lower() 

    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku zdjęcia tła pod ścieżką: {image_path}")
        # Program będzie kontynuował działanie z czarnym tłem awaryjnym
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd podczas ładowania tła: {e}")
        # Program będzie kontynuował działanie z czarnym tłem awaryjnym

def show_message(title, message, button_text, monitor_index=0):
    root = tk.Tk()
    _setup_fullscreen_bg(root, monitor_index)
    
    # Ramka imitująca "okienko" na środku ekranu
    frame = tk.Frame(root, bg='white', highlightbackground='black', highlightthickness=2)
    frame.place(relx=0.5, rely=0.5, anchor='center', width=600, height=350)
    
    # Ponieważ okno nie ma paska tytułowego w fullscreenie, dodaję tytuł wewnątrz
    title_label = tk.Label(frame, text=title, font=("Arial", 18, "bold"), bg='white', fg='black')
    title_label.pack(pady=(20, 10))

    label = tk.Label(frame, text=message, wraplength=540, justify="center", font=("Arial", 14), bg='white', fg='black')
    label.pack(pady=10, padx=20, expand=True)
    
    button = tk.Button(frame, text=button_text, font=("Arial", 12), command=root.destroy, bg='#EAEAEA', fg='black', relief=tk.FLAT, padx=10, pady=5)
    button.pack(pady=20)
    
    root.attributes('-topmost', True)
    root.mainloop()

def get_participant_id(prompt, monitor_index=0):
    root = tk.Tk()
    _setup_fullscreen_bg(root, monitor_index)

    frame = tk.Frame(root, bg='white', highlightbackground='black', highlightthickness=2)
    frame.place(relx=0.5, rely=0.5, anchor='center', width=500, height=280)

    title_label = tk.Label(frame, text="Identyfikator Uczestnika", font=("Arial", 18, "bold"), bg='white', fg='black')
    title_label.pack(pady=(20, 10))

    tk.Label(frame, text=prompt, font=("Arial", 12), bg='white', fg='black').pack(pady=5)
    
    entry_var = tk.StringVar(root)
    entry = tk.Entry(frame, textvariable=entry_var, font=("Arial", 14), width=30, justify='center')
    entry.pack(pady=15)
    entry.focus_force()

    participant_id = None
    def on_ok(event=None):
        nonlocal participant_id
        participant_id = entry_var.get()
        root.destroy()

    root.bind('<Return>', on_ok)
    button = tk.Button(frame, text="Zatwierdź", font=("Arial", 12), command=on_ok, bg='#EAEAEA', fg='black', relief=tk.FLAT, padx=20, pady=5)
    button.pack(pady=10)
    
    root.attributes('-topmost', True)
    root.mainloop()

    return participant_id

def select_monitor(default_index=0):
    try:
        num_displays = len(get_monitors())
    except ScreenInfoError:
        num_displays = 1
    
    if num_displays <= 1:
        return default_index

    root = tk.Tk()
    _setup_fullscreen_bg(root, default_index)
    
    frame = tk.Frame(root, bg='white', highlightbackground='black', highlightthickness=2)
    frame.place(relx=0.5, rely=0.5, anchor='center', width=500, height=300)

    title_label = tk.Label(frame, text="Wybór Monitora", font=("Arial", 18, "bold"), bg='white', fg='black')
    title_label.pack(pady=(20, 10))

    label = tk.Label(frame, text="Wykryto wiele monitorów.\nProszę wybrać monitor...", font=("Arial", 12), bg='white', fg='black', wraplength=430)
    label.pack(pady=10)
    
    options = [f"Monitor {i}" for i in range(num_displays)]
    selected_var = tk.StringVar(root)
    selected_var.set(options[default_index])
    
    dropdown = tk.OptionMenu(frame, selected_var, *options)
    dropdown.config(font=("Arial", 11), bg="white", relief=tk.FLAT, width=15)
    dropdown.pack(pady=10)

    button = tk.Button(frame, text="Zatwierdź", font=("Arial", 12), command=root.destroy, bg='#EAEAEA', fg='black', relief=tk.FLAT, padx=20, pady=5)
    button.pack(pady=15)
    
    root.attributes('-topmost', True)
    root.mainloop()
    
    try:
        selected_index = int(selected_var.get().split(' ')[1])
    except (ValueError, IndexError):
        selected_index = default_index
    return selected_index

def wait_for_calibration_confirmation():
    root = tk.Tk()
    _setup_fullscreen_bg(root, 0)

    frame = tk.Frame(root, bg='white', highlightbackground='black', highlightthickness=2)
    frame.place(relx=0.5, rely=0.5, anchor='center', width=600, height=280)

    title_label = tk.Label(frame, text="Kalibracja", font=("Arial", 18, "bold"), bg='white', fg='black')
    title_label.pack(pady=(20, 10))

    label_text = "Trwa kalibracja eyetrackera...\n\nPo jej pomyślnym zakończeniu, kliknij przycisk poniżej."
    label = tk.Label(frame, text=label_text, font=("Arial", 12), bg='white', fg='black')
    label.pack(pady=10, padx=20)

    button = tk.Button(frame, text="Kalibracja Zakończona, Kontynuuj", font=("Arial", 12), command=root.destroy, bg='#EAEAEA', fg='black', relief=tk.FLAT, padx=20, pady=10)
    button.pack(pady=15)
    
    root.attributes('-topmost', True)
    root.after(50, root.lower)
    root.mainloop()


def browse_file(title, filetypes):
    return filedialog.askopenfilename(title=title, filetypes=filetypes)

def browse_directory(title):
    return filedialog.askdirectory(title=title)

def show_info(title, message):
    messagebox.showinfo(title, message)

class AnalysisGUI:
    def __init__(self, run_individual_callback, run_group_callback):
        self.root = tk.Tk()
        _setup_fullscreen_bg(self.root, 0)
        
        # Callbacki do logiki biznesowej
        self.run_individual_callback = run_individual_callback
        self.run_group_callback = run_group_callback
        
        self._setup_ui()

    def _setup_ui(self):
        self.frame = tk.Frame(self.root, bg='white', highlightbackground='black', highlightthickness=2)
        self.frame.place(relx=0.5, rely=0.5, anchor='center', width=500, height=400)

        tk.Label(self.frame, text="System analizy wyników", font=("Arial", 18, "bold"), bg='white', fg='black').pack(pady=(20, 10))
        tk.Label(self.frame, text="Wybierz typ analizy", font=("Arial", 14), bg='white', fg='black').pack(pady=5)
        
        btn_indiv = tk.Button(self.frame, text="Analiza Indywidualna\n(Pojedynczy plik)", 
                              command=self.run_individual_callback, height=3, width=25, bg='#EAEAEA', font=("Arial", 11))
        btn_indiv.pack(pady=15)
        
        btn_group = tk.Button(self.frame, text="Analiza Grupowa\n(Folder z plikami Subject_*)", 
                              command=self.run_group_callback, height=3, width=25, bg='#EAEAEA', font=("Arial", 11))
        btn_group.pack(pady=10)
        
        self.status_label = tk.Label(self.frame, text="Gotowy", fg="gray", bg='white', font=("Arial", 10))
        self.status_label.pack(side="bottom", pady=15)

        self.exit_button = tk.Button(
            self.root, 
            text="✕", 
            font=("Arial", 12, "bold"),
            command=self.root.destroy, 
            bg="#cc0000", 
            fg="white",
            relief=tk.FLAT, 
            width=4,
            activebackground="#ff0000",
            activeforeground="white"
        )
        self.exit_button.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)
        

    def set_status(self, text):
        self.status_label.config(text=text)
    
    def refresh(self):
        self.root.update()

    def show_report_window(self, text_content):
        win = tk.Toplevel(self.root)
        win.title("Raport")
        win.geometry(_get_center_geometry(600, 700))
        win.configure(bg='white')
        
        text_area = tk.Text(win, wrap="word", padx=15, pady=15, font=("Arial", 11))
        text_area.pack(expand=True, fill="both")
        text_area.insert("1.0", text_content)
        text_area.config(state="disabled")

    def run(self):
        self.root.mainloop()