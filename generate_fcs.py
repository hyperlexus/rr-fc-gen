import hashlib
import json
import multiprocessing
import time
import os


def pid_to_fc(pid: int) -> int:
    if pid == 0: return 0
    pid_bytes = pid.to_bytes(4, byteorder='little', signed=False)
    buffer = pid_bytes + b'JCMR'
    high = (hashlib.md5(buffer).digest()[0] >> 1)
    return (high << 32) | pid


def generate_and_write_chunk(task_info):
    file_index, start_pid, end_pid = task_info
    process_id = os.getpid()
    file_name = f"data_chunk_{file_index}.json"

    print(f"[p{process_id}] starting {file_index}: pids {start_pid:,} to {end_pid - 1:,} into {file_name}")

    count = 0
    with open(file_name, 'w') as f:
        f.write('{')
        is_first_item = True
        for i in range(start_pid, end_pid):
            if not is_first_item:
                f.write(',')

            key = str(i)
            value = str(pid_to_fc(i)).zfill(12)

            f.write(f'{json.dumps(key)}:{json.dumps(value)}')

            is_first_item = False
            count += 1

        f.write('}')

    print(f"[p{process_id}] task {file_index} finished: wrote {count:,} items to {file_name}")


def generate_fcs():
    TOTAL_PIDS = 1_000_000_000
    NUM_FILES = 100
    NUM_PROCESSES = 10

    pids_per_file = TOTAL_PIDS // NUM_FILES

    print(f"putting {TOTAL_PIDS:,} pids into {NUM_FILES} files with {pids_per_file:,} pids per file and using {NUM_PROCESSES} parallel processes.")
    start_time = time.time()

    tasks = []
    for i in range(NUM_FILES):
        file_index = i + 1
        start_pid = i * pids_per_file + 1
        end_pid = start_pid + pids_per_file

        if file_index == NUM_FILES:
            end_pid = TOTAL_PIDS + 1

        tasks.append((file_index, start_pid, end_pid))

    # makes processes and distributes 100 tasks
    with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
        pool.map(generate_and_write_chunk, tasks)

    end_time = time.time()
    print(f"\n{NUM_FILES} files created successfully in {end_time - start_time:.2f} seconds. your poor cpu :(")
