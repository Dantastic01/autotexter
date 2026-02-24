import tkinter as tk
from tkinter import scrolledtext, ttk
import pyautogui
import random
import time
import threading
from collections import deque, Counter
import keyboard
from datetime import datetime, timedelta
import json
import os

pyautogui.FAILSAFE = True

class AutoTexter:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Texter Pro")
        self.root.geometry("600x700")
        self.running = False
        self.messages = []
        self.used_messages = []  # Messages used >2 times
        self.history = deque(maxlen=50)
        self.message_usage = Counter()  # Track FULL sentence frequency
        self.last_message_update = None
        self.timer_label = None
        self.timer_thread = None
        self.data_file = "texter_data.json"
        self.load_data()

        self.setup_gui()
        self.update_status()

    def setup_gui(self):
        # Messages input
        tk.Label(self.root, text="Active Messages (one per line):").pack(pady=5)
        self.msg_text = scrolledtext.ScrolledText(self.root, height=6, width=70)
        self.msg_text.pack(pady=5)
        self.msg_text.bind('<KeyRelease>', self.on_message_change)

        # Used Messages display (read-only)
        tk.Label(self.root, text="Overused Messages (>2 uses):").pack(pady=(10,0))
        self.used_msgs_box = scrolledtext.ScrolledText(self.root, height=4, width=70, state="disabled", bg="#ffe6e6")
        self.used_msgs_box.pack(pady=5)

        # Delay settings
        delay_frame = tk.Frame(self.root)
        delay_frame.pack(pady=5)
        
        tk.Label(delay_frame, text="Delay (seconds):").pack(side=tk.LEFT)
        self.delay_var = tk.StringVar(value="120")
        tk.Entry(delay_frame, textvariable=self.delay_var, width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Label(delay_frame, text="Inactivity hours:").pack(side=tk.LEFT)
        self.inactivity_var = tk.StringVar(value="2")
        tk.Entry(delay_frame, textvariable=self.inactivity_var, width=10).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        self.start_btn = tk.Button(btn_frame, text="Start", command=self.start_auto, bg="green", fg="white")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_auto, state="disabled", bg="red", fg="white")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # History
        tk.Label(self.root, text="Message History:").pack(pady=5)
        self.history_box = scrolledtext.ScrolledText(self.root, height=5, width=70, state="disabled")
        self.history_box.pack(pady=5)

        # Stats
        self.stats_label = tk.Label(self.root, text="Ready | Used msgs: 0")
        self.stats_label.pack(pady=5)

        # Timer
        tk.Label(self.root, text="Timer:").pack(pady=(10,0))
        self.timer_label = tk.Label(self.root, text="00:00", font=("Arial", 18, "bold"), fg="red")
        self.timer_label.pack(pady=5)

        self.status = tk.Label(self.root, text="Ready")
        self.status.pack(pady=5)

    def on_message_change(self, event=None):
        self.last_message_update = datetime.now()
        self.save_data()

    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.message_usage = Counter(data.get('message_usage', {}))
                    self.used_messages = data.get('used_messages', [])
                    self.last_message_update = datetime.fromisoformat(data.get('last_update')) if data.get('last_update') else None
        except:
            pass

    def save_data(self):
        data = {
            'message_usage': dict(self.message_usage),
            'used_messages': self.used_messages,
            'last_update': self.last_message_update.isoformat() if self.last_message_update else None
        }
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def get_effective_delay(self):
        if not self.last_message_update:
            return float(self.delay_var.get())
        
        inactivity_hours = float(self.inactivity_var.get())
        time_since_update = (datetime.now() - self.last_message_update).total_seconds() / 3600
        
        if time_since_update > inactivity_hours:
            return 240  # 4 minutes
        return float(self.delay_var.get())

    def update_status(self):
        used_count = len(self.used_messages)
        delay = self.get_effective_delay()
        auto_mode = " (AUTO 4MIN)" if delay == 240 else ""
        self.stats_label.config(text=f"Used msgs: {used_count} | Delay: {delay}s{auto_mode}")

    def update_used_messages_display(self):
        self.used_msgs_box.config(state="normal")
        self.used_msgs_box.delete("1.0", tk.END)
        for msg in self.used_messages:
            self.used_msgs_box.insert(tk.END, f"{msg} (x{self.message_usage[msg]})\n")
        self.used_msgs_box.config(state="disabled")
        self.used_msgs_box.see(tk.END)
        self.update_status()

    def check_and_move_overused(self, msg):
        """Check if message used >2 times and move to used list"""
        self.message_usage[msg] += 1
        if self.message_usage[msg] > 2 and msg not in self.used_messages:
            self.used_messages.append(msg)
            self.update_used_messages_display()
        self.save_data()

    def choose_message(self):
        recent_msgs = set(list(self.history)[-5:])
        candidates = [m for m in self.messages if m not in recent_msgs and m not in self.used_messages]
        if not candidates:
            candidates = [m for m in self.messages if m not in recent_msgs]
        if not candidates:
            candidates = self.messages
        return random.choice(candidates)

    def clear_all(self):
        self.history.clear()
        self.message_usage.clear()
        self.used_messages.clear()
        self.save_data()
        self.update_used_messages_display()
        self.history_box.config(state="normal")
        self.history_box.delete("1.0", tk.END)
        self.history_box.config(state="disabled")

    def start_timer(self, duration):
        def countdown():
            total_seconds = int(duration)
            while total_seconds > 0 and self.running:
                mins, secs = divmod(total_seconds, 60)
                time_str = f"{mins:02d}:{secs:02d}"
                self.timer_label.config(text=time_str)
                self.root.update_idletasks()
                time.sleep(1)
                total_seconds -= 1
            
            if self.running:
                self.send_next_message()
        
        self.timer_thread = threading.Thread(target=countdown, daemon=True)
        self.timer_thread.start()

    def send_next_message(self):
        msg = self.choose_message()
        
        pyautogui.write(msg, interval=0.01)
        time.sleep(0.05)
        pyautogui.press('enter')
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'enter')
        
        self.log_history(msg)
        self.check_and_move_overused(msg)
        
        self.timer_label.config(text="SENDING...")
        self.root.update_idletasks()
        time.sleep(0.5)
        
        delay = self.get_effective_delay()
        self.start_timer(delay)

    def start_auto(self):
        text = self.msg_text.get("1.0", tk.END).strip()
        self.messages = [msg.strip() for msg in text.split('\n') if msg.strip()]
        if not self.messages:
            self.status.config(text="Add messages first!")
            return

        self.last_message_update = datetime.now()
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Running...")
        
        delay = self.get_effective_delay()
        self.start_timer(delay)

    def stop_auto(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.config(text="Stopped")
        self.timer_label.config(text="STOPPED")

    def log_history(self, msg):
        self.history.append(msg)
        self.history_box.config(state="normal")
        self.history_box.delete("1.0", tk.END)
        for m in list(self.history):
            self.history_box.insert(tk.END, f"{m}\n")
        self.history_box.config(state="disabled")
        self.history_box.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTexter(root)

    def start_from_hotkey():
        if not app.running:
            app.start_auto()

    keyboard.add_hotkey('alt+num 1', start_from_hotkey)
    keyboard.add_hotkey('alt+num 2', lambda: app.stop_auto())

    root.mainloop()
