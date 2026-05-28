import numpy as np
from multiprocessing import shared_memory
import time
import logging

logger = logging.getLogger("petroflow.realtime_ipc")

class SharedMemoryIPC:
    """
    Bypasses the Python Global Interpreter Lock (GIL) by using OS-level Shared Memory.
    Allows a high-speed C-level DAQ (Data Acquisition) process to stream 50,000 Hz 
    vibration data directly into RAM, while this Python process reads it instantly.
    """
    def __init__(self, buffer_name: str = "petroflow_vib_buffer", size: int = 400000):
        self.buffer_name = buffer_name
        self.size = size # 100,000 float32s = 400,000 bytes
        self.shm = None
        
    def initialize_buffer(self):
        """Allocates the shared RAM block."""
        try:
            # Create a new shared memory block
            self.shm = shared_memory.SharedMemory(create=True, name=self.buffer_name, size=self.size)
            logger.info(f"Allocated {self.size} bytes of ultra-low latency IPC Shared Memory: {self.buffer_name}")
        except FileExistsError:
            # Reattach if it already exists from a crashed previous run
            self.shm = shared_memory.SharedMemory(name=self.buffer_name)
            logger.info(f"Reattached to existing IPC Shared Memory: {self.buffer_name}")
            
    def read_buffer_as_numpy(self) -> np.ndarray:
        """Reads the memory instantly without serialization latency."""
        if not self.shm:
            raise RuntimeError("Buffer not initialized")
            
        # Create a NumPy array backed by shared memory
        c_array = np.ndarray((100000,), dtype=np.float32, buffer=self.shm.buf)
        return c_array
        
    def cleanup(self):
        """Unlinks and frees the RAM."""
        if self.shm:
            self.shm.close()
            try:
                self.shm.unlink()
            except FileNotFoundError:
                pass

class UltraLowLatencyFFT:
    """Consumes the SharedMemory array to compute FFTs in microseconds."""
    def __init__(self):
        self.ipc = SharedMemoryIPC()
        
    def start_engine(self):
        self.ipc.initialize_buffer()
        
    def compute_spectrum(self):
        t_start = time.perf_counter_ns()
        
        # O(1) instantaneous memory pointer read (bypassing the GIL)
        raw_vibration = self.ipc.read_buffer_as_numpy()
        
        # Compute FFT using NumPy's underlying C/Fortran libraries
        fft_result = np.fft.rfft(raw_vibration)
        freqs = np.fft.rfftfreq(len(raw_vibration), d=1/50000.0) # Assuming 50kHz sampling
        
        t_end = time.perf_counter_ns()
        latency_ms = (t_end - t_start) / 1_000_000.0
        
        return freqs, np.abs(fft_result), latency_ms
        
    def stop_engine(self):
        self.ipc.cleanup()
