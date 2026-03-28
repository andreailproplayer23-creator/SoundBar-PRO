import customtkinter as ctk
from tkinter import filedialog, messagebox
import pygame
import os
import json
import keyboard
import threading
import time
import sounddevice as sd
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# Inizializzazione Mixer HQ
try:
    pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.mixer.init()
except:
    pygame.mixer.init()

CONFIG_FILE = "soundbar_config.json"

class SoundSlot(ctk.CTkFrame):
    def __init__(self, master, slot_id, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.slot_id = slot_id
        self.app = app_instance
        self.file_path = None
        self.sound = None
        self.is_playing = False
        self.is_paused = False
        self.duration = 0
        self.current_pos = 0
        self.last_update_time = 0
        self.hotkey = None
        self.volume = 0.7

        self.label = ctk.CTkLabel(self, text=f"SLOT {slot_id+1}", font=("Inter", 12, "bold"), text_color="#1DB954")
        self.label.pack(pady=(10, 2))

        self.track_name = ctk.CTkLabel(self, text="Vuoto", font=("Inter", 10), text_color="gray", height=20)
        self.track_name.pack()

        self.progress = ctk.CTkProgressBar(self, width=160, height=5, progress_color="#1DB954", fg_color="#3e3e3e")
        self.progress.set(0)
        self.progress.pack(pady=5)

        self.timer_label = ctk.CTkLabel(self, text="00:00 / 00:00", font=("Consolas", 10))
        self.timer_label.pack()

        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=5)

        self.play_btn = ctk.CTkButton(self.ctrl_frame, text="▶", width=50, height=35, fg_color="#1DB954", text_color="black", command=self.toggle_play)
        self.play_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ctk.CTkButton(self.ctrl_frame, text="⏹", width=50, height=35, fg_color="#3e3e3e", command=self.stop_sound)
        self.stop_btn.grid(row=0, column=1, padx=5)

        self.vol_slider = ctk.CTkSlider(self, from_=0, to=1, height=15, width=130, command=self.set_volume)
        self.vol_slider.set(self.volume)
        self.vol_slider.pack(pady=5)

        self.hk_btn = ctk.CTkButton(self, text="SET HOTKEY", width=130, height=22, font=("Inter", 9), fg_color="#282828", command=self.start_binding)
        self.hk_btn.pack(pady=2)
        
        self.load_btn = ctk.CTkButton(self, text="CARICA AUDIO", width=130, height=22, fg_color="transparent", border_width=1, command=self.load)
        self.load_btn.pack(pady=(2, 10))

    def clear_slot(self):
        self.stop_sound()
        if self.hotkey:
            try: keyboard.remove_hotkey(self.hotkey)
            except: pass
        self.file_path = None
        self.sound = None
        self.hotkey = None
        self.track_name.configure(text="Vuoto")
        self.hk_btn.configure(text="SET HOTKEY", fg_color="#282828")
        self.progress.set(0)
        self.update_timer_ui(0)

    def load(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("Audio HQ", "*.mp3 *.wav *.ogg")])
        if path:
            try:
                self.file_path = path
                self.sound = pygame.mixer.Sound(path)
                self.duration = self.sound.get_length()
                self.sound.set_volume(self.volume)
                name = os.path.basename(path)
                self.track_name.configure(text=(name[:16]+'..') if len(name)>16 else name)
                self.update_timer_ui(0)
                self.app.refresh_occupied_list()
                self.app.save_config()
            except: pass

    def set_volume(self, val):
        self.volume = float(val)
        if self.sound: self.sound.set_volume(self.volume)
        self.app.save_config()

    def toggle_play(self):
        if not self.sound: return
        chan = pygame.mixer.Channel(self.slot_id)
        if not self.is_playing and not self.is_paused:
            chan.play(self.sound)
            self.is_playing = True
            self.last_update_time = time.time()
            threading.Thread(target=self.update_loop, daemon=True).start()
        elif self.is_playing:
            chan.pause()
            self.is_playing = False
            self.is_paused = True
        elif self.is_paused:
            chan.unpause()
            self.is_playing = True
            self.is_paused = False
            self.last_update_time = time.time()
        self.play_btn.configure(text="⏸" if self.is_playing else "▶")

    def stop_sound(self):
        pygame.mixer.Channel(self.slot_id).stop()
        self.is_playing = False
        self.is_paused = False
        self.current_pos = 0
        self.progress.set(0)
        self.update_timer_ui(0)
        self.play_btn.configure(text="▶")

    def update_loop(self):
        while (self.is_playing or self.is_paused) and self.current_pos < self.duration:
            if self.is_playing:
                now = time.time()
                self.current_pos += now - self.last_update_time
                self.last_update_time = now
                self.progress.set(min(self.current_pos / self.duration, 1.0))
                self.update_timer_ui(self.current_pos)
            time.sleep(0.05)
        if self.current_pos >= self.duration:
            self.stop_sound()

    def update_timer_ui(self, current):
        cur_str = time.strftime('%M:%S', time.gmtime(max(0, current)))
        tot_str = time.strftime('%M:%S', time.gmtime(self.duration))
        self.timer_label.configure(text=f"{cur_str} / {tot_str}")

    def start_binding(self):
        self.hk_btn.configure(text="PREMI...", fg_color="#1DB954", text_color="black")
        threading.Thread(target=self.wait_for_key, daemon=True).start()

    def wait_for_key(self):
        key = keyboard.read_event(suppress=True).name
        self.app.check_and_remove_duplicate_hotkey(key, self.slot_id)
        if self.hotkey:
            try: keyboard.remove_hotkey(self.hotkey)
            except: pass
        self.hotkey = key
        keyboard.add_hotkey(self.hotkey, self.toggle_play)
        self.hk_btn.configure(text=f"KEY: {self.hotkey.upper()}", fg_color="#282828", text_color="white")
        self.app.save_config()

class SoundBarPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SoundBar PRO")
        self.after(0, lambda: self.state('zoomed')) 
        ctk.set_appearance_mode("dark")
        
        # Intercettiamo la chiusura della finestra
        self.protocol('WM_DELETE_WINDOW', self.hide_window)

        # --- HEADER ---
        self.header = ctk.CTkFrame(self, fg_color="#121212", height=100, corner_radius=0)
        self.header.pack(pady=0, fill="x")
        ctk.CTkLabel(self.header, text="🔊 SOUNDBAR PRO", font=("Inter", 24, "bold"), text_color="#1DB954").pack(side="left", padx=30)

        # GESTIONE SLOT
        self.manage_frame = ctk.CTkFrame(self.header, fg_color="#181818", border_width=1, border_color="#282828")
        self.manage_frame.pack(side="left", padx=20, pady=10)
        self.occupied_var = ctk.StringVar(value="Nessun sound")
        self.occupied_menu = ctk.CTkOptionMenu(self.manage_frame, variable=self.occupied_var, values=["Nessun sound"], width=180, fg_color="#282828")
        self.occupied_menu.grid(row=0, column=0, padx=10, pady=5)
        self.delete_btn = ctk.CTkButton(self.manage_frame, text="ELIMINA", width=70, fg_color="#e74c3c", command=self.delete_selected_sound)
        self.delete_btn.grid(row=0, column=1, padx=10, pady=5)

        # DEVICES
        self.audio_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.audio_frame.pack(side="right", padx=30)
        outputs = self.get_devices(kind='output')
        self.out_menu = ctk.CTkOptionMenu(self.audio_frame, values=outputs, width=220, fg_color="#282828", button_color="#1DB954")
        self.out_menu.grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.audio_frame, text="USCITA:", font=("Inter", 10)).grid(row=0, column=0, padx=5)
        inputs = self.get_devices(kind='input')
        self.in_menu = ctk.CTkOptionMenu(self.audio_frame, values=inputs, width=220, fg_color="#282828", button_color="#3498db")
        self.in_menu.grid(row=1, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.audio_frame, text="MICROFONO:", font=("Inter", 10)).grid(row=1, column=0, padx=5)

        # GRIGLIA
        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(padx=20, pady=20, fill="both", expand=True)
        self.slots = []
        for i in range(50):
            s = SoundSlot(self.container, slot_id=i, app_instance=self, fg_color="#181818", corner_radius=15, border_width=1, border_color="#282828")
            s.grid(row=i//5, column=i%5, padx=10, pady=10, sticky="nsew")
            self.slots.append(s)

        for i in range(5): self.container.grid_columnconfigure(i, weight=1)

        self.load_config()
        self.refresh_occupied_list()
        
        # Avvia l'icona tray in un thread separato
        self.create_tray_icon()

    def hide_window(self):
        self.withdraw() # Nasconde la finestra ma non chiude il processo

    def show_window(self):
        self.deiconify()
        self.state('zoomed')

    def quit_app(self):
        self.tray_icon.stop()
        self.destroy()
        os._exit(0)

    def create_tray_icon(self):
        # Crea un'icona semplice se non hai il file .ico sottomano
        image = Image.new('RGB', (64, 64), color=(29, 185, 84))
        d = ImageDraw.Draw(image)
        d.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
        
        menu = (item('Mostra SoundBar', self.show_window, default=True), item('Esci', self.quit_app))
        self.tray_icon = pystray.Icon("soundbar", image, "SoundBar PRO", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def get_devices(self, kind='output'):
        try:
            devices = sd.query_devices()
            filtered = [d['name'] for d in devices if (kind == 'output' and d['max_output_channels'] > 0) or (kind == 'input' and d['max_input_channels'] > 0)]
            return sorted(list(set(filtered)))
        except: return ["Default"]

    def refresh_occupied_list(self):
        occupied = [f"Slot {s.slot_id+1}: {os.path.basename(s.file_path)}" for s in self.slots if s.file_path]
        self.occupied_menu.configure(values=occupied if occupied else ["Nessun sound"])
        if occupied and self.occupied_var.get() not in occupied: self.occupied_var.set(occupied[0])

    def delete_selected_sound(self):
        selection = self.occupied_var.get()
        if selection == "Nessun sound": return
        slot_num = int(selection.split(":")[0].replace("Slot ", "")) - 1
        self.slots[slot_num].clear_slot()
        self.refresh_occupied_list()
        self.save_config()

    def check_and_remove_duplicate_hotkey(self, key, current_id):
        for s in self.slots:
            if s.slot_id != current_id and s.hotkey == key:
                s.hotkey = None
                s.hk_btn.configure(text="SET HOTKEY")

    def save_config(self):
        data = {str(s.slot_id): {"path": s.file_path, "hotkey": s.hotkey, "volume": s.volume} for s in self.slots}
        with open(CONFIG_FILE, "w") as f: json.dump(data, f)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    for s in self.slots:
                        c = data.get(str(s.slot_id))
                        if c:
                            s.volume = c.get("volume", 0.7)
                            s.vol_slider.set(s.volume)
                            if c.get("hotkey"):
                                s.hotkey = c["hotkey"]
                                s.hk_btn.configure(text=f"KEY: {s.hotkey.upper()}")
                                keyboard.add_hotkey(s.hotkey, s.toggle_play)
                            if c.get("path") and os.path.exists(c["path"]): s.load(c["path"])
            except: pass
        self.refresh_occupied_list()

if __name__ == "__main__":
    app = SoundBarPro()
    app.mainloop()