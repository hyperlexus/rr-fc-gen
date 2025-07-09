import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def pid_to_fc(pid: int) -> int:
    if pid == 0: return 0
    pid_bytes = pid.to_bytes(4, byteorder='little', signed=False)
    buffer = pid_bytes + b'JCMR'
    high = (hashlib.md5(buffer).digest()[0] >> 1)
    return (high << 32) | pid

def generate_pid_fc_entry(pid: int, start_time, total_pids) -> dict:
    if pid % max(100000, (total_pids/25)) == 0:
        print(f"{pid} fcs generated. took {(time.time() - start_time) / 60:.2f} minutes since start")
    return {str(pid): f"{pid_to_fc(pid):012}"}

def generate_fcs(number_pids):
    output_filename = "data.json"

    if os.path.exists(output_filename):
        os.remove(output_filename)
        print(f"removed existing '{output_filename}'.")

    genstring = f"generating fcs for {number_pids} pids... takes approximately {0.22*(number_pids/1000000) + 0.15*(number_pids/1000000):.2f} minutes."
    print(genstring)
    start_time = time.time()
    all_generated_data = []

    with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
        futures = {executor.submit(generate_pid_fc_entry, i, start_time, number_pids): i for i in range(1, number_pids + 1)}

        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                all_generated_data.append(result)
            except Exception as e:
                print(f"PID {futures[future]} generated an exception: {e}")

    all_generated_data.sort(key=lambda x: int(list(x.keys())[0]))

    with open(output_filename, 'w') as f:
        json.dump(all_generated_data, f)
    print(f"wrote {len(all_generated_data)} fcs to '{output_filename}'.")

    print(f"done. took {(time.time() - start_time) / 60:.2f} minutes.")