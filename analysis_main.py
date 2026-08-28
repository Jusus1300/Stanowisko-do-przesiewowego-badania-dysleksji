import analysis_individual
import analysis_group
import tkinter_module as ui

class AnalysisController:
    def __init__(self):
        # Inicjalizacja GUI z przekazaniem funkcji (callbacków) do przycisków
        self.gui = ui.AnalysisGUI(
            run_individual_callback=self.run_individual,
            run_group_callback=self.run_group
        )

    def run_individual(self):
        filepath = ui.browse_file(
            title="Wybierz plik surowych danych (czytanie_tekstu...)",
            filetypes=[("CSV Files", "*.csv")]
        )
        if filepath:
            self.gui.set_status("Przetwarzanie...")
            self.gui.refresh()
            
            # Wywołanie logiki analizy
            report = analysis_individual.run_analysis(filepath)
            
            # Aktualizacja UI
            self.gui.show_report_window(report)
            self.gui.set_status("Zakończono")

    def run_group(self):
        folderpath = ui.browse_directory(title="Wybierz folder z danymi badanych")
        if folderpath:
            self.gui.set_status("Przetwarzanie grupy...")
            self.gui.refresh()
            
            # Wywołanie logiki analizy
            result_msg = analysis_group.run_analysis(folderpath)
            
            # Aktualizacja UI
            ui.show_info("Wynik Analizy Grupowej", result_msg)
            self.gui.set_status("Zakończono")

    def start(self):
        self.gui.run()

if __name__ == "__main__":
    print("Uruchamianie Systemu Analizy Okulograficznej...")
    app = AnalysisController()
    app.start()