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
import multiprocessing
import duckdb
import random
import ctypes
import shutil

TOTAL_PIDS = 1_000_000_000
NUM_CHUNKS = 100
NUM_PROCESSES = os.cpu_count()

DB_FILE = 'fc-gen-resources/friend_codes.db'
MATCHES_FILE = 'fc-gen-resources/matches.json'
FORMATTED_MATCHES_FILE = 'fc-gen-resources/matches.txt'
CHUNK_DIR = 'fc-gen-resources/temp_chunks'
C_FILE = 'c_stuff/fc_gen.dll'

# big thanks to ki for all the help <3
# props to daniel for making the db half the size and the search 10x faster

try:
    c_lib = ctypes.CDLL(os.path.abspath(C_FILE))
    c_lib.generate_csv_chunk.argtypes = [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_char_p
    ]
except Exception as e:
    print(f"warn: {e}")


def format_fc(fc_str: str) -> str:
    return f"{fc_str[0:4]}-{fc_str[4:8]}-{fc_str[8:12]}"

def fc_to_pid(fc_str: str) -> int:
    return int(fc_str) & 0xFFFFFFFF

def generate_and_write_chunk_task(task_info):
    file_index, start_pid, end_pid, chunk_dir = task_info
    file_name = os.path.join(chunk_dir, f"data_chunk_{file_index}.csv")

    c_filepath = file_name.encode('utf-8')
    c_lib.generate_csv_chunk(start_pid, end_pid, c_filepath)

    return file_index, end_pid - start_pid


class FriendCodeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.digit_labels = None
        self.digit_values = None
        self.generate_button = None
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
        self.process_pool = None

        if not os.path.exists('fc-gen-resources'):
            os.makedirs('fc-gen-resources')

        self.setup_ui()
        self.check_file_status()
        self.process_queue()

    def adjust_digit(self, digit_idx, delta):
        current_val = self.digit_values[digit_idx]
        new_val = current_val + delta

        # 0 = any, max is 12
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
        has_twelve_same, has_eleven_same = False, False

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

            self.example_fc_label.config(text=f"example match (NOT REAL FC): {formatted_example}", foreground="#2ecc71")

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

        # generator
        gen_frame = ttk.LabelFrame(main_frame, text="create and populate database (once, about 10GB. takes ~15min)", padding="15")
        gen_frame.pack(fill=tk.X, expand=True)

        self.generate_button = ttk.Button(gen_frame, text="run!", command=self.start_generation_thread)
        self.generate_button.pack(pady=5)

        # search area
        search_frame = ttk.LabelFrame(main_frame, text="search through all fcs", padding="15")
        search_frame.pack(fill=tk.X, expand=True, pady=15)

        # number wheel julius caesar shit
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

            btn_up = ttk.Button(columnbina, text="▲", width=2, command=lambda idx=i: self.adjust_digit(idx, 1))
            btn_up.pack(side=tk.TOP)

            val_label = ttk.Label(columnbina, text="any", font=('Consolas', 11), anchor="center", width=3)
            val_label.pack(side=tk.TOP, pady=3)
            self.digit_labels[i] = val_label

            btn_down = ttk.Button(columnbina, text="▼", width=2, command=lambda idx=i: self.adjust_digit(idx, -1))
            btn_down.pack(side=tk.TOP)

        self.example_fc_label = ttk.Label(caesar_frame, text="example match (NOT REAL FC): ????-????-????", font=('Consolas', 14, 'bold'), foreground="#5db0d7")
        self.example_fc_label.pack(pady=(15, 5))

        regex_frame = ttk.Frame(search_frame)
        regex_frame.pack(fill=tk.X, expand=True, pady=(10, 0))
        ttk.Label(regex_frame, text="using regex (optional, takes ~15min): ").pack(side=tk.LEFT)
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
                self.progress_label.config(
                    text=f"{message['action']}: {percentage:.2f}% ({message['current']:,}/{message['total']:,})")
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
                messagebox.showinfo("Success", message["text"])
                self.set_ui_busy(False)
            elif msg_type == "operation_cancelled":
                self.progress_bar.stop()
                self.progress_label.config(text="operation was cancelled")
                self.set_ui_busy(False)
            elif msg_type == "error":
                self.progress_bar.stop()
                self.progress_label.config(text="Error")
                messagebox.showerror("Error", message["text"])
                print(message["text"])
                self.set_ui_busy(False)

            if msg_type not in ["progress", "indeterminate_progress"]:
                self.check_file_status()

        # "trust me it's good practice, you can leave it, it will not explode in your face"
        except queue.Empty:
            pass
        self.after(100, self.process_queue)

    def start_generation_thread(self):
        if os.path.exists(DB_FILE):
            if not messagebox.askyesno("are you sure bro", f"regenerate database? it already exists at {DB_FILE}"):
                return
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.generate_codes_task, daemon=True).start()

    def start_search_thread(self):
        self.match_count_label.config(text="matches found: no")
        self.set_ui_busy(True, show_cancel=True)
        self.stop_event.clear()
        threading.Thread(target=self.search_codes_task, daemon=True).start()

    def start_formatting_thread(self):
        self.set_ui_busy(True)
        self.stop_event.clear()
        threading.Thread(target=self.format_matches_task, daemon=True).start()

    def generate_codes_task(self):
        try:
            start_time = time.time()
            if not os.path.exists(CHUNK_DIR): os.makedirs(CHUNK_DIR)

            pids_per_chunk = TOTAL_PIDS // NUM_CHUNKS
            tasks = []
            # optimise optimise optimise
            for i in range(NUM_CHUNKS):
                start_pid = i * pids_per_chunk + 1
                end_pid = start_pid + pids_per_chunk
                if i == NUM_CHUNKS - 1: end_pid = TOTAL_PIDS + 1
                tasks.append((i, start_pid, end_pid, CHUNK_DIR))

            with multiprocessing.Pool(processes=NUM_PROCESSES) as self.process_pool:
                async_results = [self.process_pool.apply_async(generate_and_write_chunk_task, args=(task,)) for task in tasks]
                self.process_pool.close()

                completed_chunks = 0
                while completed_chunks < len(tasks):
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
                        {"type": "progress", "action": "generating chunks", "current": completed_chunks, "total": NUM_CHUNKS})
                    time.sleep(0.1)

                self.process_pool.join()
            self.process_pool = None

            if self.stop_event.is_set():
                self.thread_queue.put({"type": "operation_cancelled"})
                return

            self.thread_queue.put({"type": "indeterminate_progress", "action": "combining chunks into db"})

            if os.path.exists(DB_FILE): os.remove(DB_FILE)

            duckdb_tmp = os.path.join(CHUNK_DIR, 'duckdb_tmp')
            if not os.path.exists(duckdb_tmp):
                os.makedirs(duckdb_tmp)

            conn = duckdb.connect(DB_FILE, config={
                'temp_directory': duckdb_tmp,
                'preserve_insertion_order': False
            })

            conn.execute(f"PRAGMA threads={NUM_PROCESSES}")
            conn.execute("PRAGMA memory_limit='60GB'")
            conn.execute("PRAGMA enable_progress_bar")

            conn.execute(f"""
                CREATE TABLE fcs AS 
                SELECT fc, bitmask 
                FROM read_csv('{CHUNK_DIR}/*.csv', 
                    columns={{'fc': 'VARCHAR', 'bitmask': 'UBIGINT'}}, 
                    header=false
                ) 
                ORDER BY bitmask
            """)
            conn.close()

            # cleanup
            for i in range(NUM_CHUNKS):
                chunk_path = os.path.join(CHUNK_DIR, f'data_chunk_{i}.csv')
                if os.path.exists(chunk_path): os.remove(chunk_path)

            if os.path.exists(duckdb_tmp):
                shutil.rmtree(duckdb_tmp)
            os.rmdir(CHUNK_DIR)

            end_time = time.time()
            msg = f"Generated & Indexed {TOTAL_PIDS:,} codes in {end_time - start_time:.2f}s."
            self.thread_queue.put({"type": "stop_indeterminate"})
            self.thread_queue.put({"type": "operation_complete", "text": msg})
        except Exception as e:
            if not self.stop_event.is_set():
                self.thread_queue.put({"type": "error", "text": f"failed to generate with error: {e}"})

    def search_codes_task(self):
        try:
            start_time = time.time()
            self.thread_queue.put({"type": "indeterminate_progress", "action": "scanning through database"})

            conditions = []

            for digit, count in self.digit_values.items():
                if count > 0:
                    shift_amount = digit * 4
                    conditions.append(f"((bitmask >> {shift_amount}) & 15) >= {count}")

            pattern = self.pattern_entry.get().strip()
            use_python_regex = False
            compiled_pattern = None

            if pattern:
                try:
                    compiled_pattern = re.compile(pattern)
                    if "\\" in pattern:
                        use_python_regex = True
                    else:
                        conditions.append(f"regexp_matches(fc, '{pattern}')")
                except re.error as e:
                    self.thread_queue.put({"type": "error", "text": f"Invalid Regex:\n{e}"})
                    return

            query = "SELECT fc FROM fcs"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            conn = duckdb.connect(DB_FILE)
            cursor = conn.execute(query)  # fetchall() very bad idea

            matches_found = 0
            is_first_match = True
            rows_scanned = 0

            with open(MATCHES_FILE, 'w') as outfile:
                outfile.write('{')
                matches_ui_component_updated = False

                while True:
                    if self.stop_event.is_set():
                        conn.close()
                        self.thread_queue.put({"type": "operation_cancelled"})
                        return

                    chunk = cursor.fetchmany(100000)
                    if not chunk:
                        break

                    for (fc,) in chunk:
                        rows_scanned += 1

                        if use_python_regex and compiled_pattern:
                            if not compiled_pattern.search(fc):
                                continue

                        matches_found += 1
                        if matches_found and not matches_ui_component_updated:
                            self.thread_queue.put({"type": "match_count_update", "bool": "yes"})
                            matches_ui_component_updated = True

                        pid = fc_to_pid(fc)
                        formatted_fc = format_fc(fc)

                        if not is_first_match:
                            outfile.write(',')
                        outfile.write(f'"{pid}": "{formatted_fc}"')
                        is_first_match = False

                    if use_python_regex and not conditions and rows_scanned % 5_000_000 == 0:
                        self.thread_queue.put({"type": "indeterminate_progress", "action": f"scanning, {rows_scanned:,} out of 1 billion rows done, {time.time() - start_time:.1f}s elapsed."})

                outfile.write('}')

            conn.close()

            end_time = time.time()
            msg = f"found {matches_found:,} matches in {end_time - start_time:.4f}s."

            self.thread_queue.put({"type": "stop_indeterminate"})
            self.thread_queue.put({"type": "match_count_update", "bool": matches_found})
            self.thread_queue.put({"type": "operation_complete", "text": msg})

        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"search failed with error: {e}"})

    def format_matches_task(self):
        try:
            self.thread_queue.put({"type": "indeterminate_progress", "action": "formatting..."})
            with open(MATCHES_FILE, 'r') as f:
                matches = json.load(f)

            with open(FORMATTED_MATCHES_FILE, 'w') as f:
                f.write(f"Friend codes from search at {str(datetime.now())[:-7]} (total matches: {len(matches)}):\n\n")
                for i, (pid, code) in enumerate(matches.items()):
                    f.write(f"{pid} -> {code}\n")

            self.thread_queue.put({"type": "stop_indeterminate"})
            self.thread_queue.put({"type": "operation_complete", "text": f"formatted {len(matches)} matches as txt to {FORMATTED_MATCHES_FILE}"})
        except Exception as e:
            self.thread_queue.put({"type": "error", "text": f"Formatting failed: {e}"})

    def cancel_operation(self):
        self.progress_label.config(text="cancelling...")
        self.stop_event.set()
        if self.process_pool:
            self.process_pool.terminate()

    def set_ui_busy(self, is_busy, show_cancel=False):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.generate_button.config(state=state)
        self.search_button.config(state=state)
        self.format_button.config(state=state)
        self.pattern_entry.config(state=state)

        # bitch stop crashing
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
        if self.process_pool:
            self.cancel_operation()
        self.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = FriendCodeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
