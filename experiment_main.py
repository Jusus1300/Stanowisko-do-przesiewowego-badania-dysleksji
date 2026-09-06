import sys
import os
import csv
from datetime import datetime
from gazepoint import GazeTracker
import tkinter_module as ui
import experiment_module as exp
import experiment_config as cfg

def save_behavioral_result(filepath, trial_num, result):
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['NumerProby', 'Odpowiedz', 'CzyPoprawna', 'CzasReakcji_s'])
        user_answer, is_correct, reaction_time = result
        writer.writerow([trial_num, user_answer, is_correct, round(reaction_time, 3)])

def main():
    selected_monitor = ui.select_monitor(default_index=cfg.DEFAULT_MONITOR_INDEX)
    participant_id = ui.get_participant_id(
        "Wprowadź swój kryptonim kadeta (np. 'kadet_01'):",
        monitor_index=selected_monitor
    )

    if not participant_id or not participant_id.strip():
        print("[INFO] Nie podano kryptonimu. Aplikacja zostanie zamknięta.")
        sys.exit()
    
    try:
        clean_participant_id = "".join(c for c in participant_id if c.isalnum() or c in ('_','-')).rstrip()
        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = f"{clean_participant_id}_{timestamp_str}"
        participant_folder = os.path.join(cfg.DATA_FOLDER, folder_name)
        os.makedirs(participant_folder, exist_ok=True)
        print(f"[INFO] Wyniki zostaną zapisane w folderze: {participant_folder}")
        behavioral_path = os.path.join(participant_folder, cfg.BEHAVIORAL_RESULTS_FILENAME)

        tracker = GazeTracker(host=cfg.GAZEPOINT_HOST, port=cfg.GAZEPOINT_PORT)

        ui.show_message(
            title="Witaj w Akademii Kosmicznej!",
            message=f"Witaj w symulatorze, kadecie {participant_id}!\n\nTwoja pierwsza misja treningowa zaraz się rozpocznie.",
            button_text="Przejdź do synchronizacji skanera",
            monitor_index=selected_monitor
        )
        
        tracker.connect()
        tracker.calibrate()
        ui.wait_for_calibration_confirmation()

        
        ui.show_message(
            title="Synchronizacja Zakończona",
            message="Skaner wzrokowy zsynchronizowany.\nHełm jest gotowy do misji.\n\nKliknij 'Start', aby otrzymać odprawę.",
            button_text="Start",
            monitor_index=selected_monitor
        )
        
        experiment = exp.PygameExperiment(tracker, selected_monitor, participant_folder)
        
        experiment.run_reading_screen()
        
        result = experiment.run_question_screen()
        save_behavioral_result(behavioral_path, trial_num=1, result=result)
        
        experiment.run_game_instruction_screen()
        experiment.run_target_game_screen()
        
        experiment.shutdown()
        
        ui.show_message(
            title="Misja Zakończona!",
            message="Świetna robota, kadecie!\nEnergia bota G-Z3R jest stabilna.\n\nJesteś na dobrej drodze, by stać się asem kosmicznej floty!",
            button_text="Zakończ Symulację",
            monitor_index=selected_monitor
        )

    except ConnectionRefusedError:
        print("[BŁĄD KRYTYCZNY] Upewnij się, że oprogramowanie Gazepoint Control jest uruchomione.")
    except SystemExit as e:
        print(f"[INFO] Aplikacja zamknięta przez użytkownika: {e}")
    except Exception as e:
        print(f"[BŁĄD KRYTYCZNY] Wystąpił nieoczekiwany błąd: {e}")
    finally:
        if 'tracker' in locals() and tracker is not None:
            tracker.close()
        print("[INFO] Aplikacja została zamknięta.")

if __name__ == '__main__':
    main()