import pygame
import sys
import random
import os
import math
import experiment_config as cfg

class PygameExperiment:
    def __init__(self, tracker, monitor_index, participant_folder):
        self.tracker = tracker
        self.monitor_index = monitor_index
        self.participant_folder = participant_folder
        
        pygame.init()
        # Używam flag HWSURFACE i DOUBLEBUF dla płynności
        self.screen_flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), 
            self.screen_flags,
            display=self.monitor_index 
        )
        pygame.display.set_caption("Eksperyment")
        
        # Ładowanie grafik
        try:
            background = pygame.image.load(cfg.BACKGROUND_IMG).convert()
            self.background = pygame.transform.scale(background, (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
            
            target = pygame.image.load(cfg.TARGET_IMG).convert_alpha()
            self.target = pygame.transform.scale(target, (cfg.TARGET_WIDTH, cfg.TARGET_HEIGHT))
        except pygame.error as e:
            print(f"[WARN] Błąd ładowania grafiki: {e}. Program będzie działał bez grafik.")
            self.background = None
            self.target = None

    def _draw_background(self):
        # Pomocnicza funkcja do rysowania tła, aby nie powielać kodu.
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(cfg.BACKGROUND_COLOR)

    def _draw_text(self, surface, text, font_path, base_font_size, color, center_pos):
        # Pomocnicza funkcja do renderowania wielowierszowego tekstu z automatycznym skalowaniem
        # oraz dynamicznym, ciemnoszarym tłem.
        max_width = cfg.SCREEN_WIDTH * (1.0 - cfg.HORIZONTAL_MARGIN_PERCENT)
        max_height = cfg.SCREEN_HEIGHT * (1.0 - cfg.VERTICAL_MARGIN_PERCENT)
        
        font_size = base_font_size
        
        # Pętla dopasowująca rozmiar czcionki
        while True:
            try:
                font = pygame.font.Font(font_path, font_size)
            except (FileNotFoundError, pygame.error):
                font = pygame.font.Font(None, font_size)
            
            lines = []
            paragraphs = text.split('\n')
            
            for para in paragraphs:
                words = para.split(' ')
                current_line = ""
                for word in words:
                    test_line = current_line + word + " "
                    if font.size(test_line)[0] < max_width:
                        current_line = test_line
                    else:
                        lines.append(current_line.strip())
                        current_line = word + " "
                lines.append(current_line.strip())
            
            line_height = font.get_linesize() * cfg.LINE_SPACING_MULTIPLIER
            total_height = len(lines) * line_height
            
            if total_height <= max_height or font_size <= 12:
                break
            
            font_size -= 2
            
        line_surfaces = [font.render(line, True, color) for line in lines]
        
        # RYSOWANIE CIEMNOSZAREGO TŁA POD TEKSTEM
        if lines:
            # Szukam szerokości najszerszej linii tekstu
            max_line_width = max([font.size(line)[0] for line in lines])
            
            # Marginesy wewnątrz ciemnego pudełka (w pikselach)
            padding_x = 100
            padding_y = 80
            
            box_width = max_line_width + padding_x
            box_height = total_height + padding_y
            
            # Tworzę powierzchnię obsługującą przezroczystość (SRCALPHA)
            bg_rect_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            bg_rect_surface.fill((40, 40, 40, 225)) 
            
            # Rysuję obramowanie dla estetyki
            pygame.draw.rect(bg_rect_surface, (100, 100, 100, 255), bg_rect_surface.get_rect(), 2, border_radius=10)
            
            # Pobieram pozycję centrum i rysuję na głównym ekranie
            bg_rect = bg_rect_surface.get_rect(center=center_pos)
            surface.blit(bg_rect_surface, bg_rect)

        # Renderowanie linii tekstu
        top_y = center_pos[1] - total_height / 2
        for i, line_surface in enumerate(line_surfaces):
            line_rect = line_surface.get_rect(centerx=center_pos[0], top=top_y + i * line_height)
            surface.blit(line_surface, line_rect)

    def _wait_for_keypress(self, key_to_continue):
        pygame.mouse.set_visible(False)
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.tracker.close() # Bezpiecznik
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == key_to_continue:
                    waiting = False

    def run_reading_screen(self):
        raw_data_path = os.path.join(self.participant_folder, "czytanie_tekstu_dane_surowe.csv")
        events_path = os.path.join(self.participant_folder, "czytanie_tekstu_zdarzenia.csv") 
        
        try:
            with open(cfg.TEXT_FILE, 'r', encoding='utf-8') as f:
                full_text = f.read()
        except FileNotFoundError:
            full_text = "Błąd: Nie znaleziono pliku."
        
        self._draw_background()
        self._draw_text(self.screen, full_text, cfg.FONT_PATH, cfg.FONT_SIZE_PYGAME, cfg.TEXT_COLOR, self.screen.get_rect().center)
        
        pygame.display.flip() 
        
        screenshot_path = os.path.join(self.participant_folder, "zrzut_ekranu_bodzca.png")
        pygame.image.save(self.screen, screenshot_path)
        
        self.tracker.start_logging(raw_data_path, events_path, 0)
        self._wait_for_keypress(pygame.K_RETURN) 
        self.tracker.stop_logging()
        print("[INFO] Zakończono rejestrację zadania czytania.")
    
    def run_question_screen(self):
        raw_data_path = os.path.join(self.participant_folder, f"weryfikacja_dane_surowe.csv")
        events_path = os.path.join(self.participant_folder, f"weryfikacja_zdarzenia.csv")
        
        self.tracker.start_logging(raw_data_path, events_path, 1)
        self.tracker.log_event(f"QUESTION_SCREEN_START: Weryfikacja")
        
        try:
            with open(cfg.TEXT_FILE_QUESTION, 'r', encoding='utf-8') as f:
                question_text = f.read()
        except FileNotFoundError:
            question_text = "Błąd: Nie znaleziono pliku."

        self._draw_background()
        self._draw_text(self.screen, question_text, cfg.FONT_PATH, cfg.FONT_SIZE_PYGAME, cfg.TEXT_COLOR, self.screen.get_rect().center)
        pygame.display.flip()
        
        start_time = pygame.time.get_ticks()
        user_answer = None
        waiting = True
        
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                     self.tracker.close()
                     sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a: user_answer = 'A'; waiting = False
                    elif event.key == pygame.K_b: user_answer = 'B'; waiting = False
        
        end_time = pygame.time.get_ticks()
        reaction_time = (end_time - start_time) / 1000.0
        is_correct = (user_answer == 'A')
        
        self.tracker.log_event(f"ANSWER_SELECTED: {user_answer}, Correct: {is_correct}, RT: {reaction_time}")
        
        # Feedback
        feedback_text = "Dobrze!" if is_correct else "Spróbujmy następnym razem!"
        feedback_color = (0, 200, 0) if is_correct else (200, 0, 0) 
        
        self._draw_background()
        self._draw_text(self.screen, feedback_text, cfg.FONT_PATH, cfg.FONT_SIZE_PYGAME, feedback_color, self.screen.get_rect().center)
        pygame.display.flip()
        
        pygame.time.wait(2000)
        
        self.tracker.stop_logging()
        return user_answer, is_correct, reaction_time
    
    def run_game_instruction_screen(self):
        self._draw_background()

        try:
            with open(cfg.TEXT_FILE_INSTRUCTION, 'r', encoding='utf-8') as f:
                instructions = f.read()
        except FileNotFoundError:
            instructions = "Błąd: Nie znaleziono pliku."

        self._draw_text(self.screen, instructions, cfg.FONT_PATH, cfg.FONT_SIZE_PYGAME, cfg.TEXT_COLOR, self.screen.get_rect().center)
        pygame.display.flip()
        self._wait_for_keypress(pygame.K_RETURN)

    def run_target_game_screen(self):
        raw_data_path = os.path.join(self.participant_folder, "gra_dane_surowe.csv")
        events_path = os.path.join(self.participant_folder, "gra_zdarzenia.csv")
        
        self.tracker.start_logging(raw_data_path, events_path, 1)
        pygame.mouse.set_visible(False)
        self.tracker.log_event("TARGET_GAME_START")
        
        margin = 0.15
        positions = {
            'top-left': (int(cfg.SCREEN_WIDTH * margin), int(cfg.SCREEN_HEIGHT * margin)),
            'top-right': (int(cfg.SCREEN_WIDTH * (1-margin)), int(cfg.SCREEN_HEIGHT * margin)),
            'bottom-left': (int(cfg.SCREEN_WIDTH * margin), int(cfg.SCREEN_HEIGHT * (1-margin))),
            'bottom-right': (int(cfg.SCREEN_WIDTH * (1-margin)), int(cfg.SCREEN_HEIGHT * (1-margin))),
            'center': (int(cfg.SCREEN_WIDTH * 0.5), int(cfg.SCREEN_HEIGHT * 0.5))
        }
        pos_keys = list(positions.keys())
        last_pos_key = None
        
        clock = pygame.time.Clock()
        current_stability = 0
        damage_per_second = cfg.TARGET_MAX_HEALTH / cfg.TIME_TO_DESTROY_TARGET_S

        for i in range(cfg.SACCADE_TRIALS):
            if current_stability >= cfg.TARGET_MAX_HEALTH: break
            
            current_pos_key = random.choice(pos_keys)
            while current_pos_key == last_pos_key: 
                current_pos_key = random.choice(pos_keys)
            
            target_center = positions[current_pos_key]
            target_rect = pygame.Rect(
                target_center[0] - cfg.TARGET_WIDTH // 2,
                target_center[1] - cfg.TARGET_HEIGHT // 2,
                cfg.TARGET_WIDTH,
                cfg.TARGET_HEIGHT
            )
            last_pos_key = current_pos_key
            
            self.tracker.log_event(f"TRIAL_{i+1}_TARGET_SPAWN_{target_rect.centerx}_{target_rect.centery}")
            start_time = pygame.time.get_ticks()
            
            while pygame.time.get_ticks() - start_time < cfg.SACCADE_TARGET_DURATION:
                if current_stability >= cfg.TARGET_MAX_HEALTH: break
                
                delta_time_s = clock.tick(60) / 1000.0
                
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        self.tracker.close()
                        sys.exit()
                
                gaze_data = self.tracker.get_latest_gaze_data()
                gaze_x_norm, gaze_y_norm, is_gaze_valid = gaze_data['x'], gaze_data['y'], gaze_data['valid']
                
                gaze_x_clamped = max(0.0, min(1.0, gaze_x_norm))
                gaze_y_clamped = max(0.0, min(1.0, gaze_y_norm))
                gaze_pos_screen = (int(gaze_x_clamped * cfg.SCREEN_WIDTH), int(gaze_y_clamped * cfg.SCREEN_HEIGHT))
                
                is_damaging = False
                if target_rect.collidepoint(gaze_pos_screen) and is_gaze_valid:
                    healing_this_frame = damage_per_second * delta_time_s
                    current_stability += healing_this_frame
                    is_damaging = True

                self._draw_background()

                if self.target:
                    self.screen.blit(self.target, target_rect.topleft)
                else:
                    pygame.draw.rect(self.screen, (200, 200, 0), target_rect, border_radius=30)
                
                stability_ratio = min(1, current_stability / cfg.TARGET_MAX_HEALTH)
                health_bar_current_width = int(cfg.HEALTH_BAR_WIDTH * stability_ratio)
                health_bar_bg_rect = pygame.Rect(cfg.SCREEN_WIDTH // 2 - cfg.HEALTH_BAR_WIDTH // 2, 40, cfg.HEALTH_BAR_WIDTH, cfg.HEALTH_BAR_HEIGHT)
                health_bar_fg_rect = pygame.Rect(cfg.SCREEN_WIDTH // 2 - cfg.HEALTH_BAR_WIDTH // 2, 40, health_bar_current_width, cfg.HEALTH_BAR_HEIGHT)
                
                pygame.draw.rect(self.screen, cfg.HEALTH_BAR_COLOR_EMPTY, health_bar_bg_rect, border_radius=5)
                pygame.draw.rect(self.screen, cfg.HEALTH_BAR_COLOR_FULL, health_bar_fg_rect, border_radius=5)

                base_radius = 15
                cursor_radius = base_radius
                if is_damaging:
                    pulse_speed = 8; pulse_amplitude = 4
                    pulse = math.sin(pygame.time.get_ticks() / 1000 * pulse_speed) * pulse_amplitude
                    cursor_radius = int(base_radius + pulse)
                
                cursor_color = (255, 100, 100) if is_gaze_valid else (80, 80, 80)
                pygame.draw.circle(self.screen, cursor_color, gaze_pos_screen, cursor_radius, 2)
                
                pygame.display.flip()
            
            if current_stability >= cfg.TARGET_MAX_HEALTH:
                self.tracker.log_event("TARGET_GAME_SUCCESS_TARGET_STABILIZED")
                break

        if current_stability < cfg.TARGET_MAX_HEALTH: 
            self.tracker.log_event("TARGET_GAME_FAIL_TIME_UP")
        
        pygame.mouse.set_visible(True)
        self._draw_background()
        pygame.display.flip()
        pygame.time.wait(200)
        
        self.tracker.log_event("TARGET_GAME_END")
        self.tracker.stop_logging()

    def shutdown(self):
        pygame.quit()