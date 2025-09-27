import tkinter as tk
from tkinter import ttk, messagebox
import sv_ttk
import threading
import queue
import json
import os
import re
import time
from datetime import datetime
import hashlib
import multiprocessing


def pid_to_fc(pid: int) -> str:
    if pid == 0: return "000000000000"
    pid_bytes = pid.to_bytes(4, byteorder='little', signed=False)
    buffer = pid_bytes + b'JCMR'
    high = (hashlib.md5(buffer).digest()[0] >> 1)
    full_fc_int = (high << 32) | pid
    fc_str = str(full_fc_int)[-12:].zfill(12)
    return fc_str


def format_fc(fc_str: str) -> str:
    return f"{fc_str[0:4]}-{fc_str[4:8]}-{fc_str[8:12]}"


def generate_and_write_chunk_task(task_info):
    file_index, start_pid, end_pid, chunk_dir = task_info
    file_name = os.path.join(chunk_dir, f"data_chunk_{file_index}.txt")

    count = 0
    with open(file_name, 'w') as f:
        for i in range(start_pid, end_pid):
            fc = pid_to_fc(i)
            f.write(f"{fc}\n")
            count += 1
    return file_index, count


TOTAL_PIDS = 1_000_000_000
NUM_CHUNKS = 100
NUM_PROCESSES = os.cpu_count()  # number of cpu cores it uses, you can alternatively change this to smth like 4 if you want your pc to be usable

FINAL_DATA_FILE = 'fc-gen-resources/final_data.txt'
MATCHES_FILE = 'fc-gen-resources/matches.json'
FORMATTED_MATCHES_FILE = 'fc-gen-resources/matches.txt'
CHUNK_DIR = 'fc-gen-resources/temp_chunks'


class FriendCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        sv_ttk.set_theme("dark")

        self.title("rr-fc-gen")
        self.geometry("600x650")
        self.resizable(False, True)

        # self.style = ttk.Style(self)
        # self.style.theme_use('vista')
        # self.style.configure("TButton", padding=6, relief="flat", background="#0078D7", foreground="white",
        #                      font=('Segoe UI', 10))
        # self.style.map("TButton", background=[('active', '#005a9e')])
        # self.style.configure("TLabel", font=('Segoe UI', 10))
        # self.style.configure("TEntry", font=('Segoe UI', 10), padding=5)
        # self.style.configure("TFrame", background="#f0f0f0")
        # self.style.configure("Cancel.TButton", background="#dc3545", foreground="white")
        # self.style.map("Cancel.TButton", background=[('active', '#c82333')])

        self.thread_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.process_pool = None

        self.setup_ui()
        self.check_file_status()
        self.process_queue()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- fc gen ---
        gen_frame = ttk.LabelFrame(main_frame, text="1: generate all fcs (once)", padding="15")
        gen_frame.pack(fill=tk.X, expand=True)

        self.generate_button = ttk.Button(gen_frame, text="generate 1bil fcs!", command=self.start_generation_thread)
        self.generate_button.pack(pady=5)

        # --- pattern finder ---
        search_frame = ttk.LabelFrame(main_frame, text="2: search using a regex pattern", padding="15")
        search_frame.pack(fill=tk.X, expand=True, pady=15)

        ttk.Label(search_frame, text="Enter Regex Pattern:").pack()
        self.pattern_entry = ttk.Entry(search_frame, width=50)
        self.pattern_entry.pack(pady=5)
        self.pattern_entry.insert(0, r"(\d)\1{3}")  # example: any digit repeated 4 times
        self.search_button = ttk.Button(search_frame, text="search!", command=self.start_search_thread)
        self.search_button.pack(pady=5)
        self.match_count_label = ttk.Label(search_frame, text="matches found: 0")
        self.match_count_label.pack(pady=5)

        # --- format ---
        format_frame = ttk.LabelFrame(main_frame, text="3: format matches and make them readable", padding="15")
        format_frame.pack(fill=tk.X, expand=True)
        self.format_button = ttk.Button(format_frame, text=f"format matches!",
                                        command=self.start_formatting_thread)
        self.format_button.pack(pady=5)

        self.status_label = ttk.Label(self, text="ready", padding="10", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # --- progress bar ---
        progress_frame = ttk.LabelFrame(main_frame, padding="15")
        progress_frame.pack(fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="progress: -")
        self.progress_label.pack(pady=(5, 0))
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=300, mode='determinate')
        self.progress_bar.pack(pady=5, padx=10)
        self.cancel_button = ttk.Button(progress_frame, text="cancel", style="Cancel.TButton", command=self.cancel_operation)

    def process_queue(self):
        try:
            message = self.thread_queue.get_nowait()
            msg_type = message.get("type")

            if msg_type == "progress":
                self.progress_bar['value'] = message["current"]
                self.progress_bar['maximum'] = message["total"]
                # self.progress_label.config(text=f"Progress: {message['current']}/{message['total']}")
                percentage = f"{'{:.2f}'.format(message['current']/message['total']*100)}%"
                current_formatted = f"{message["current"] if message["total"] < 1_000_000 else str(message["current"]/1_000_000) + "m"}"
                self.progress_label.config(text=f"Progress: {percentage} / {current_formatted}")
            elif msg_type == "status_update":
                self.status_label.config(text=message["text"])
            elif msg_type == "match_count_update":
                self.match_count_label.config(text=f"matches found: {message['count']:,}")
            elif msg_type == "operation_complete":
                messagebox.showinfo("Success", message["text"])
                self.set_ui_busy(False)
            elif msg_type == "operation_cancelled":
                messagebox.showwarning("rip", "the operation was cancelled.")
                self.set_ui_busy(False)
            elif msg_type == "error":
                messagebox.showerror("error", message["text"])
                self.set_ui_busy(False)

            if msg_type not in ["progress", "status_update"]:
                self.check_file_status()

        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def start_generation_thread(self):
        if os.path.exists(FINAL_DATA_FILE):
            if not messagebox.askyesno("Confirm", f"{FINAL_DATA_FILE} already exists. make a new one?"):
                return
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.generate_codes_task, daemon=True).start()

    def start_search_thread(self):
        pattern = self.pattern_entry.get()
        if not pattern:
            messagebox.showwarning("pattern empty", "please provide a regex pattern")
            return
        try:
            re.compile(pattern)
        except re.error as e:
            messagebox.showerror("Invalid Regex", f"your regex pattern doesn't work:\n{e}")
            return

        self.match_count_label.config(text="matches found: 0")
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.search_codes_task, args=(pattern,), daemon=True).start()

    def start_formatting_thread(self):
        self.set_ui_busy(True)
        self.stop_event.clear()
        threading.Thread(target=self.format_matches_task, daemon=True).start()

    def generate_codes_task(self):
        try:
            start_time = time.time()
            self.thread_queue.put({"type": "status_update", "text": "generating..."})

            if not os.path.exists(CHUNK_DIR): os.makedirs(CHUNK_DIR)

            pids_per_chunk = TOTAL_PIDS // NUM_CHUNKS
            tasks = []
            for i in range(NUM_CHUNKS):
                start_pid = i * pids_per_chunk + 1
                end_pid = start_pid + pids_per_chunk
                if i == NUM_CHUNKS - 1: end_pid = TOTAL_PIDS + 1
                tasks.append((i, start_pid, end_pid, CHUNK_DIR))

            self.thread_queue.put({"type": "progress", "current": 0, "total": NUM_CHUNKS})

            with multiprocessing.Pool(processes=NUM_PROCESSES) as self.process_pool:
                async_results = [self.process_pool.apply_async(generate_and_write_chunk_task, args=(task,)) for task in tasks]
                self.process_pool.close()

                completed_chunks = 0
                while completed_chunks < len(tasks):  # runs until everything is generated (for better cancel responsiveness)
                    if self.stop_event.is_set():
                        self.process_pool.terminate()
                        self.thread_queue.put({"type": "operation_cancelled"})
                        return

                    remaining_results = []
                    for res in async_results:
                        if res.ready():
                            completed_chunks += 1
                        else:
                            remaining_results.append(res)

                    async_results = remaining_results

                    self.thread_queue.put(
                        {"type": "status_update", "text": f"chunk {completed_chunks}/{NUM_CHUNKS} done"})
                    self.thread_queue.put({"type": "progress", "current": completed_chunks, "total": NUM_CHUNKS})

                    # LETS JUST CONSUME ALL THE CPU ON THE THREAD HAHAHAHAHAHA
                    time.sleep(0.1)
                    # time.sleep(1)

                self.process_pool.join()

            self.process_pool = None

            self.thread_queue.put({"type": "status_update", "text": "Merging chunks..."})
            with open(FINAL_DATA_FILE, 'w') as outfile:
                for i in range(NUM_CHUNKS):
                    chunk_path = os.path.join(CHUNK_DIR, f'data_chunk_{i}.txt')
                    with open(chunk_path, 'r') as infile: outfile.write(infile.read())  # wtf am i writing btw???
                    os.remove(chunk_path)
            os.rmdir(CHUNK_DIR)

            end_time = time.time()
            msg = f"generated {TOTAL_PIDS:,} codes in {end_time - start_time:.2f}s."
            self.thread_queue.put({"type": "operation_complete", "text": msg})
        except Exception as e:
            if not self.stop_event.is_set():
                self.thread_queue.put({"type": "error", "text": f"failed to generate. error: {e}"})

    def search_codes_task(self, pattern_str):
        try:
            start_time = time.time()
            self.thread_queue.put({"type": "status_update", "text": f"checking pattern and searching"})
            pattern = re.compile(pattern_str)
            matches_found = 0
            is_first_match = True
            last_found_fc = "-"

            with open(FINAL_DATA_FILE, 'r') as infile, open(MATCHES_FILE, 'w') as outfile:
                outfile.write('{')

                for line_num, line in enumerate(infile, 1):
                    if self.stop_event.is_set():
                        self.thread_queue.put({"type": "operation_cancelled"})
                        return

                    fc = line.strip()
                    if pattern.search(fc):
                        matches_found += 1
                        formatted_fc = format_fc(fc)
                        last_found_fc = formatted_fc

                        if not is_first_match:
                            outfile.write(',')

                        outfile.write(f'"{line_num}":{json.dumps(formatted_fc)}')
                        is_first_match = False

                    if line_num % 250000 == 0:
                        status_text = f"scanned {line_num:,} codes... (last match: {last_found_fc})"
                        self.thread_queue.put({"type": "status_update", "text": status_text})
                        self.thread_queue.put({"type": "progress", "current": line_num, "total": TOTAL_PIDS})
                        self.thread_queue.put({"type": "match_count_update", "count": matches_found})
                outfile.write('}')

            end_time = time.time()
            msg = f"found {matches_found:,} matches in {end_time - start_time:.2f}s."
            self.thread_queue.put({"type": "match_count_update", "count": matches_found})
            self.thread_queue.put({"type": "operation_complete", "text": msg})
        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"search failed: {e}"})

    def format_matches_task(self):
        try:
            self.thread_queue.put({"type": "status_update", "text": "formatting..."})
            with open(MATCHES_FILE, 'r') as f:
                matches = json.load(f)

            with open(FORMATTED_MATCHES_FILE, 'w') as f:
                f.write(f"friend codes from search at {str(datetime.now())[:-7]} (total matches: {len(matches)}):\n\n")  # goofy ah
                for i, (pid, code) in enumerate(matches.items()):
                    f.write(f"{pid} -> {code}\n")

            self.thread_queue.put(
                {"type": "operation_complete", "text": f"formatted {len(matches)} matches to {FORMATTED_MATCHES_FILE}"})
        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"formatting failed: {e}"})

    def cancel_operation(self):
        self.status_label.config(text="cancelling...")  # yes, 2 l
        self.stop_event.set()
        if self.process_pool:
            self.process_pool.terminate()

    def set_ui_busy(self, is_busy, show_cancel=False):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.generate_button.config(state=state)
        self.search_button.config(state=state)
        self.format_button.config(state=state)
        self.pattern_entry.config(state=state)

        if show_cancel and is_busy:
            self.cancel_button.pack(pady=5)
        else:
            self.cancel_button.pack_forget()

        if not is_busy:
            self.status_label.config(text="ready")
            self.progress_bar['value'] = 0
            self.progress_label.config(text="progress: -")
            self.check_file_status()

    def check_file_status(self):
        final_data_exists = os.path.exists(FINAL_DATA_FILE)
        matches_exist = os.path.exists(MATCHES_FILE)

        search_state = tk.NORMAL if final_data_exists else tk.DISABLED
        self.search_button.config(state=search_state)
        self.pattern_entry.config(state=tk.DISABLED if search_state == tk.DISABLED else tk.NORMAL)

        self.format_button.config(state=tk.NORMAL if matches_exist else tk.DISABLED)

    def on_closing(self):
        if self.process_pool:
            self.cancel_operation()
        self.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = FriendCodeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
