import pygame

class AudioEngine:
    def __init__(self):
        pygame.mixer.init()
        self.sounds = {}

    def load_sound(self, slot_id, file_path):
        try:
            self.sounds[slot_id] = pygame.mixer.Sound(file_path)
            print(f"Slot {slot_id} caricato: {file_path}")
        except Exception as e:
            print(f"Errore caricamento: {e}")

    def play_sound(self, slot_id):
        if slot_id in self.sounds:
            self.sounds[slot_id].play()
        else:
            print(f"Slot {slot_id} vuoto!")

    def stop_all(self):
        pygame.mixer.stop()