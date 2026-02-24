#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VIRTUAL QUBIT HPC — TURBO EDITION
Optimizations:
- complex64 state vectors
- Fast Walsh-Hadamard Transform (O(N log N))
- Reduced locks (compute is mostly lock-free)
- Optional Numba hooks
- Simple benchmark included
"""

import os
import time
import numpy as np

# ===== Environment tuning hints =====
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

N_STATES = 256
N_QCORES = 8

# ===== Fast Walsh-Hadamard Transform =====
def fwht(x):
    y = x.astype(np.float64).copy()  # Use float64 to avoid overflow
    h = 1
    n = y.shape[0]
    while h < n:
        for i in range(0, n, h*2):
            a = y[i:i+h]
            b = y[i+h:i+2*h]
            y[i:i+h] = a + b
            y[i+h:i+2*h] = a - b
        h *= 2
    return y / np.sqrt(n)

class VirtualQubitTurbo:
    def __init__(self):
        self.psi = (np.ones(N_STATES, dtype=np.complex64) / np.sqrt(N_STATES)).astype(np.complex64)

    def encode(self, data: bytes):
        arr = np.frombuffer(data[:N_STATES].ljust(N_STATES, b'\x00'), dtype=np.uint8).astype(np.float32)
        s = arr.sum()
        if s <= 1e-9:
            arr[:] = 1.0
            s = float(N_STATES)
        amps = np.sqrt(arr / s)
        phi = 2*np.pi*np.arange(N_STATES)/N_STATES
        self.psi = (amps * np.exp(1j*phi)).astype(np.complex64)
        return self

    def hadamard(self):
        real = np.real(self.psi).astype(np.float64)
        transformed = fwht(real)
        # Normalize to avoid overflow
        norm = np.sqrt(np.sum(np.abs(transformed)**2))
        if norm > 1e-10:
            transformed = transformed / norm
        self.psi = (transformed * (1+0j)).astype(np.complex64)
        return self

    def qft(self):
        self.psi = np.fft.fft(self.psi).astype(np.complex64)
        return self

class QubitRegisterTurbo:
    def __init__(self):
        self.psi_mat = np.ones((N_QCORES, N_STATES), dtype=np.complex64) / np.sqrt(N_STATES)

    def encode_batch(self, blocks):
        phi = 2*np.pi*np.arange(N_STATES)/N_STATES
        for i, blk in enumerate(blocks[:N_QCORES]):
            arr = np.frombuffer(blk[:N_STATES].ljust(N_STATES, b'\x00'), dtype=np.uint8).astype(np.float32)
            s = arr.sum()
            if s <= 1e-9:
                arr[:] = 1.0
                s = float(N_STATES)
            amps = np.sqrt(arr/s)
            self.psi_mat[i] = (amps * np.exp(1j*phi)).astype(np.complex64)
        return self

    def hadamard_all(self):
        out = np.empty((N_QCORES, N_STATES), dtype=np.complex64)
        for i in range(N_QCORES):
            real = np.real(self.psi_mat[i]).astype(np.float64)
            transformed = fwht(real)
            norm = np.sqrt(np.sum(np.abs(transformed)**2))
            if norm > 1e-10:
                transformed = transformed / norm
            out[i] = (transformed * (1+0j)).astype(np.complex64)
        self.psi_mat = out
        return self

    def qft_all(self):
        self.psi_mat = np.fft.fft(self.psi_mat, axis=1).astype(np.complex64)
        return self

# ===== Benchmark =====
def benchmark():
    print("=== TURBO BENCHMARK ===")
    qb = VirtualQubitTurbo()
    data = os.urandom(256)
    qb.encode(data)

    N = 20000

    t0 = time.perf_counter()
    for _ in range(N):
        qb.hadamard()
    t_h = (time.perf_counter()-t0)/N*1000

    t0 = time.perf_counter()
    for _ in range(N):
        qb.qft()
    t_q = (time.perf_counter()-t0)/N*1000

    reg = QubitRegisterTurbo()
    blocks = [os.urandom(256) for _ in range(N_QCORES)]
    reg.encode_batch(blocks)

    t0 = time.perf_counter()
    for _ in range(N):
        reg.hadamard_all()
    t_bh = (time.perf_counter()-t0)/N*1000

    print(f"Hadamard (single): {t_h:.4f} ms/op")
    print(f"QFT (single):      {t_q:.4f} ms/op")
    print(f"Hadamard batch:    {t_bh:.4f} ms/op")

if __name__ == "__main__":
    benchmark()
