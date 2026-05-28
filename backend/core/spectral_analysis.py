import numpy as np
from scipy.fftpack import fft, fftfreq
from scipy.signal import hilbert, butter, filtfilt, spectrogram
from sklearn.ensemble import IsolationForest

class BearingFrequencyDetector:
    """Calculates bearing fault frequencies (BPFO, BSF, FTF)."""
    @staticmethod
    def calculate_frequencies(rpm: float, n_rollers: int, roller_diameter: float, pitch_diameter: float, contact_angle_deg: float) -> dict:
        """
        Calculate fundamental bearing defect frequencies.
        BPFO: Ball Pass Frequency Outer
        BPFI: Ball Pass Frequency Inner
        BSF: Ball Spin Frequency
        FTF: Fundamental Train Frequency (Cage speed)
        """
        rps = rpm / 60.0
        angle_rad = np.radians(contact_angle_deg)
        ratio = (roller_diameter / pitch_diameter) * np.cos(angle_rad)
        
        ftf = (rps / 2.0) * (1.0 - ratio)
        bpfo = n_rollers * ftf
        bpfi = (n_rollers * rps / 2.0) * (1.0 + ratio)
        bsf = (pitch_diameter / (2.0 * roller_diameter)) * rps * (1.0 - ratio**2)
        
        return {
            "FTF": ftf,
            "BPFO": bpfo,
            "BPFI": bpfi,
            "BSF": bsf,
            "1X": rps
        }

class EnvelopeAnalyzer:
    """Performs envelope analysis (demodulation) for early defect detection."""
    @staticmethod
    def apply_envelope(signal: np.ndarray, fs: float, lowcut: float, highcut: float) -> tuple:
        """
        Applies a bandpass filter around a resonance frequency, then extracts the envelope using the Hilbert transform.
        Returns the envelope signal and its spectrum.
        """
        # 1. Bandpass Filter
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(4, [low, high], btype='band')
        filtered_signal = filtfilt(b, a, signal)
        
        # 2. Hilbert Transform for Demodulation
        analytic_signal = hilbert(filtered_signal)
        envelope = np.abs(analytic_signal)
        
        # 3. FFT of the Envelope
        n = len(envelope)
        envelope_fft = np.abs(fft(envelope))[:n//2] * 2.0 / n
        freqs = fftfreq(n, 1.0/fs)[:n//2]
        
        # Remove DC component
        envelope_fft[0] = 0
        
        return envelope, freqs, envelope_fft

class SpectrogramGenerator:
    """Generates time-frequency spectrograms for transient analysis."""
    @staticmethod
    def generate(signal: np.ndarray, fs: float, nperseg: int = 256):
        """
        Computes the spectrogram of the signal.
        Returns frequencies, times, and spectrogram matrix.
        """
        frequencies, times, Sxx = spectrogram(signal, fs=fs, nperseg=nperseg)
        # Convert to dB
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        return frequencies, times, Sxx_db

class SignatureAnomalyDetector:
    """Uses IsolationForest to detect anomalies based on spectral signatures."""
    def __init__(self, contamination=0.05):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.is_trained = False
        
    def train(self, spectral_features: np.ndarray):
        """Train the Isolation Forest on baseline spectral features."""
        if len(spectral_features) > 0:
            self.model.fit(spectral_features)
            self.is_trained = True
            
    def predict(self, spectral_features: np.ndarray) -> np.ndarray:
        """Predict if the features are anomalous (-1) or normal (1)."""
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction.")
        return self.model.predict(spectral_features)

class SyntheticSignalGenerator:
    """Creates mock vibration signals with controllable defect frequencies."""
    @staticmethod
    def generate_signal(fs: float, duration: float, rpm: float, defect_freq: float = 0.0, noise_level: float = 0.5) -> tuple:
        """
        Generate a synthetic vibration signal.
        Includes 1X running speed and an optional defect frequency with harmonics.
        """
        t = np.linspace(0, duration, int(fs * duration), endpoint=False)
        rps = rpm / 60.0
        
        # Baseline vibration (1X running speed + some harmonics)
        signal = 1.5 * np.sin(2 * np.pi * rps * t)
        signal += 0.5 * np.sin(2 * np.pi * 2 * rps * t)
        
        # Add defect signature
        if defect_freq > 0:
            # Impact modulated by resonance (e.g., 3000 Hz resonance)
            resonance = 3000.0
            impacts = np.zeros_like(t)
            impact_interval = int(fs / defect_freq)
            
            for i in range(0, len(t), impact_interval):
                if i < len(t):
                    impacts[i] = 5.0  # Impact amplitude
            
            # Simple exponential decay response
            decay = np.exp(-1000 * t[:int(fs*0.01)]) * np.sin(2 * np.pi * resonance * t[:int(fs*0.01)])
            defect_signal = np.convolve(impacts, decay, mode='same')
            signal += defect_signal
            
        # Add Gaussian white noise
        signal += np.random.normal(0, noise_level, len(t))
        
        return t, signal
