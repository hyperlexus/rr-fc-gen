import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import threading
import queue
import json
import os
import time
from datetime import datetime
import duckdb
import random
import urllib.request


DB_URL = "https://dl.hyperlexus.uk/friend_codes.db"
DB_FILE = 'fc-gen-resources/friend_codes.db'
MATCHES_FILE = 'fc-gen-resources/matches.json'
FORMATTED_MATCHES_FILE = 'fc-gen-resources/matches.txt'

def format_fc(fc_str: str) -> str:
    return f"{fc_str[0:4]}-{fc_str[4:8]}-{fc_str[8:12]}"

def fc_to_pid(fc_str: str) -> int:
    return int(fc_str) & 0xFFFFFFFF


class FriendCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.digit_labels = None
        self.digit_values = None
        self.download_button = None
        self.cancel_button = None
        self.progress_bar = None
        self.progress_label = None
        self.example_fc_label = None
        sv_ttk.set_theme("dark")

        self.title("rr-fc-gen")
        self.geometry("650x700")
        self.resizable(False, True)

        self.thread_queue = queue.Queue()
        self.stop_event = threading.Event()

        if not os.path.exists('fc-gen-resources'):
            os.makedirs('fc-gen-resources')

        self.setup_ui()
        self.check_file_status()
        self.process_queue()

    def adjust_digit(self, digit_idx, delta):
        current_val = self.digit_values[digit_idx]
        new_val = current_val + delta

        if new_val < 0:
            new_val = 12
        elif new_val > 12:
            new_val = 0

        self.digit_values[digit_idx] = new_val
        display_text = "any" if new_val == 0 else str(new_val)
        self.digit_labels[digit_idx].config(text=display_text)
        self.update_example_fc()

    def update_example_fc(self):
        required_digits = []
        total_inputted = 0
        has_twelve_same = False

        for digit in range(10):
            count = self.digit_values[digit]
            if count == 12:
                has_twelve_same = True
            if count > 0:
                required_digits.extend([str(digit)] * count)
                total_inputted += count

        if total_inputted > 12:
            self.example_fc_label.config(text="invalid: total exceeds 12 digits!", foreground="#e74c3c")
            self.search_button.config(state=tk.DISABLED)
        elif has_twelve_same:
            self.example_fc_label.config(text="warning: these codes are impossible.", foreground="#ffda03")
        else:
            remaining_count = 12 - total_inputted
            fillers = [str(random.randint(0, 9)) for _ in range(remaining_count)]

            all_digits = required_digits + fillers
            random.shuffle(all_digits)

            example_str = "".join(all_digits)
            formatted_example = f"{example_str[0:4]}-{example_str[4:8]}-{example_str[8:12]}"

            self.example_fc_label.config(text=f"example match: {formatted_example}", foreground="#2ecc71")
            self.check_file_status()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, expand=True, pady=(0, 15))

        self.progress_label = ttk.Label(progress_frame, text="ready", font=('', 10, 'bold'))
        self.progress_label.pack(side=tk.TOP, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=400, mode='determinate')
        self.progress_bar.pack(side=tk.TOP, fill=tk.X)

        self.cancel_button = ttk.Button(progress_frame, text="cancel", command=self.cancel_operation)

        gen_frame = ttk.LabelFrame(main_frame, text="generate database (required once, takes 3 minutes)", padding="15")
        gen_frame.pack(fill=tk.X, expand=True)

        self.download_button = ttk.Button(gen_frame, text="generate!", command=self.start_download_thread)
        self.download_button.pack(pady=5)

        search_frame = ttk.LabelFrame(main_frame, text="search through all fcs", padding="15")
        search_frame.pack(fill=tk.X, expand=True, pady=15)

        caesar_frame = ttk.LabelFrame(search_frame, text="visual search", padding="10")
        caesar_frame.pack(fill=tk.X, expand=True, pady=5)

        i_am_le_chiffre = ttk.Frame(caesar_frame)
        i_am_le_chiffre.pack(fill=tk.X, expand=True, pady=5)

        self.digit_values = {i: 0 for i in range(10)}
        self.digit_labels = {}

        for i in range(10):
            columnbina = ttk.Frame(i_am_le_chiffre)
            columnbina.pack(side=tk.LEFT, expand=True, padx=1)
            ttk.Label(columnbina, text=f"{i}", font=('', 10, 'bold')).pack(side=tk.TOP, pady=(0, 2))

            ttk.Button(columnbina, text="▲", width=2, command=lambda idx=i: self.adjust_digit(idx, 1)).pack(side=tk.TOP)

            val_label = ttk.Label(columnbina, text="any", font=('Consolas', 11), anchor="center", width=3)
            val_label.pack(side=tk.TOP, pady=3)
            self.digit_labels[i] = val_label

            ttk.Button(columnbina, text="▼", width=2, command=lambda idx=i: self.adjust_digit(idx, -1)).pack(side=tk.TOP)

        self.example_fc_label = ttk.Label(caesar_frame, text="example match: ????-????-????", font=('Consolas', 14, 'bold'), foreground="#5db0d7")
        self.example_fc_label.pack(pady=(15, 5))

        regex_frame = ttk.Frame(search_frame)
        regex_frame.pack(fill=tk.X, expand=True, pady=(10, 0))
        ttk.Label(regex_frame, text="using regex: ").pack(side=tk.LEFT)
        self.pattern_entry = ttk.Entry(regex_frame, width=35)
        self.pattern_entry.pack(side=tk.LEFT, padx=5)

        self.search_button = ttk.Button(search_frame, text="search!", command=self.start_search_thread)
        self.search_button.pack(pady=10)

        self.match_count_label = ttk.Label(search_frame, text="matches found: 0")
        self.match_count_label.pack()

        format_frame = ttk.LabelFrame(main_frame, text="format matches to txt", padding="15")
        format_frame.pack(fill=tk.X, expand=True)
        self.format_button = ttk.Button(format_frame, text="format!", command=self.start_formatting_thread)
        self.format_button.pack(pady=5)

    def process_queue(self):
        try:
            message = self.thread_queue.get_nowait()
            msg_type = message.get("type")

            if msg_type == "progress":
                self.progress_bar.config(mode='determinate')
                percentage = (message["current"] / message["total"]) * 100
                self.progress_bar['value'] = percentage

                current_gb = message['current'] / (1024 ** 3)
                total_gb = message['total'] / (1024 ** 3)
                self.progress_label.config(
                    text=f"{message['action']}: {percentage:.1f}% ({current_gb:.2f} GB / {total_gb:.2f} GB)")

            elif msg_type == "indeterminate_progress":
                self.progress_bar.config(mode='indeterminate')
                self.progress_bar.start(10)
                self.progress_label.config(text=message["action"])
            elif msg_type == "stop_indeterminate":
                self.progress_bar.stop()
                self.progress_bar.config(mode='determinate', value=0)
            elif msg_type == "match_count_update":
                self.match_count_label.config(text=f"matches found: {message['bool']}")
            elif msg_type == "operation_complete":
                self.progress_bar.stop()
                self.progress_label.config(text="")
                messagebox.showinfo("success :D", message["text"])
                self.set_ui_busy(False)
            elif msg_type == "operation_cancelled":
                self.progress_bar.stop()
                self.progress_label.config(text="operation cancelled")
                self.set_ui_busy(False)
            elif msg_type == "error":
                self.progress_bar.stop()
                self.progress_label.config(text="Error")
                messagebox.showerror("error :(", message["text"])
                self.set_ui_busy(False)

            if msg_type not in ["progress", "indeterminate_progress"]:
                self.check_file_status()

        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def start_download_thread(self):
        if os.path.exists(DB_FILE):
            if not messagebox.askyesno("Confirm", f"Redownload database? It already exists."):
                return
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.download_db_task, daemon=True).start()

    def start_search_thread(self):
        self.match_count_label.config(text="matches found: no")
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.search_codes_task, daemon=True).start()

    def start_formatting_thread(self):
        self.set_ui_busy(True)
        self.stop_event.clear()
        threading.Thread(target=self.format_matches_task, daemon=True).start()

    def download_db_task(self):
        try:
            start_time = time.time()

            req = urllib.request.Request(DB_URL, headers={'User-agent': 'rr-fc-gen-client/1.0'})

            with urllib.request.urlopen(req) as response, open(DB_FILE, 'wb') as out_file:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0

                chunk_size = 2 * 1024 * 1024
                last_update_time = 0

                while True:
                    if self.stop_event.is_set():
                        raise Exception("download cancelled manually.")

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    out_file.write(chunk)
                    downloaded += len(chunk)

                    current_time = time.time()
                    if current_time - last_update_time > 0.1 or downloaded == total_size:
                        if total_size > 0:
                            self.thread_queue.put({
                                "type": "progress",
                                "action": "generating",
                                "current": downloaded,
                                "total": total_size
                            })
                        last_update_time = current_time

            end_time = time.time()
            msg = f"generated database in {end_time - start_time:.2f}s."
            self.thread_queue.put({"type": "operation_complete", "text": msg})

        except Exception as e:
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            if not self.stop_event.is_set():
                self.thread_queue.put({"type": "error", "text": f"failed: {e}"})
            else:
                self.thread_queue.put({"type": "operation_cancelled"})

    def search_codes_task(self):
        try:
            start_time = time.time()
            self.thread_queue.put({"type": "indeterminate_progress", "action": "scanning..."})

            conditions = []
            for digit, count in self.digit_values.items():
                if count > 0:
                    shift_amount = digit * 4
                    conditions.append(f"((bitmask >> {shift_amount}) & 15) >= {count}")

            pattern = self.pattern_entry.get().strip()
            if pattern:
                safe_pattern = pattern.replace("'", "''")
                conditions.append(f"regexp_matches(fc, '{safe_pattern}')")

            query = "SELECT fc FROM fcs"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            conn = duckdb.connect(DB_FILE)
            cursor = conn.execute(query)

            matches_found = 0

            with open(MATCHES_FILE, 'w') as outfile:
                outfile.write('{')
                while True:
                    if self.stop_event.is_set():
                        conn.close()
                        self.thread_queue.put({"type": "operation_cancelled"})
                        return

                    chunk = cursor.fetchmany(100000)
                    if not chunk:
                        break

                    for i, (fc,) in enumerate(chunk):
                        matches_found += 1
                        pid = fc_to_pid(fc)
                        formatted_fc = format_fc(fc)

                        if matches_found > 1:
                            outfile.write(',')
                        outfile.write(f'"{pid}": "{formatted_fc}"')

                outfile.write('}')

            conn.close()

            end_time = time.time()
            msg = f"found {matches_found:,} matches in {end_time - start_time:.4f}s."
            self.thread_queue.put({"type": "stop_indeterminate"})
            self.thread_queue.put({"type": "match_count_update", "bool": matches_found})
            self.thread_queue.put({"type": "operation_complete", "text": msg})

        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"Search failed: {e}"})

    def format_matches_task(self):
        try:
            self.thread_queue.put({"type": "indeterminate_progress", "action": "formatting..."})
            with open(MATCHES_FILE, 'r') as f:
                matches = json.load(f)

            with open(FORMATTED_MATCHES_FILE, 'w') as f:
                f.write(f"friend codes from search at {str(datetime.now())[:-7]} (total matches: {len(matches)}):\n\n")
                for pid, code in matches.items():
                    f.write(f"{pid} -> {code}\n")

            self.thread_queue.put({"type": "stop_indeterminate"})

            message = f"formatted {len(matches)} matches as txt to {FORMATTED_MATCHES_FILE}."
            if len(matches) < 10000:
                message += " opening notepad..."
                import subprocess
                subprocess.Popen(["notepad.exe", os.path.abspath(FORMATTED_MATCHES_FILE)])

            self.thread_queue.put({"type": "operation_complete", "text": message})
        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"Formatting failed: {e}"})

    def cancel_operation(self):
        self.progress_label.config(text="cancelling...")
        self.stop_event.set()

    def set_ui_busy(self, is_busy, show_cancel=False):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.download_button.config(state=state)
        self.search_button.config(state=state)
        self.format_button.config(state=state)
        self.pattern_entry.config(state=state)

        if show_cancel and is_busy:
            self.cancel_button.pack(pady=(10, 0))
        else:
            self.cancel_button.pack_forget()

        if not is_busy:
            self.check_file_status()

    def check_file_status(self):
        db_exists = os.path.exists(DB_FILE)
        matches_exist = os.path.exists(MATCHES_FILE)

        search_state = tk.NORMAL if db_exists else tk.DISABLED
        self.search_button.config(state=search_state)
        self.pattern_entry.config(state=tk.DISABLED if search_state == tk.DISABLED else tk.NORMAL)
        self.format_button.config(state=tk.NORMAL if matches_exist else tk.DISABLED)

    def on_closing(self):
        self.cancel_operation()
        self.destroy()


if __name__ == "__main__":
    app = FriendCodeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
