import ctypes
import time

import numpy as np
import os

dll_path = os.path.abspath("c_stuff/fc_gen.dll")
print(dll_path)
try:
    c_lib = ctypes.CDLL(dll_path)
except Exception as e:
    print(f"{e}")
    exit()

c_lib.generate_chunk.argtypes = [
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint64)
]

def a():
    start,end = 152590080,162590085
    amount = end-start
    fc_b = np.empty(amount*12, dtype=np.uint8)
    m_b = np.empty(amount, dtype=np.uint64)


    print(f"pids {start} to {end-1}")
    s=time.time()
    c_lib.generate_chunk(
        start,
        end,
        fc_b.ctypes.data_as(ctypes.c_void_p),
        m_b.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64))
    )

    r = fc_b.view('S12')
    print("results obtained")
    print(len(r))
    print(time.time() - s)

if __name__ == "__main__":
    a()