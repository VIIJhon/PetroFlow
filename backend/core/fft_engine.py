"""
PetroFlow FFT & Acceleration Spectrum Generator Engine
Generates physical high-frequency accelerometer signal sequences modeling motor/pump defects
(dynamic imbalance, misalignment, bearing failures, cavitation) and runs a real FFT analysis in Python.
Authored by PetroFlow Engineering Team
"""

import numpy as np
from typing import Dict, Any, List

class FFTEngine:
    @staticmethod
    def generate_vibration_signal(
        rpm: float,
        vibration_level: float,
        defect_type: str = "nominal",
        sampling_rate: int = 2000,
        duration_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generates synthetic physical accelerometer signal (mm/s^2) based on motor speed and defects.
        """
        # Fundamental rotation frequency (Hz)
        rot_freq_hz = rpm / 60.0
        
        # Sampling settings
        n_samples = int(sampling_rate * duration_seconds)
        t = np.linspace(0.0, duration_seconds, n_samples, endpoint=False)
        
        # Base signal (low amplitude structural noise)
        np.random.seed(42)  # reproducible seed
        signal = np.random.normal(0.0, 0.05 * vibration_level, n_samples)
        
        # Inject signature frequencies according to defect types
        if defect_type == "desbalance":
            # Imbalance: 1x RPM is highly dominant
            signal += 1.2 * vibration_level * np.sin(2.0 * np.pi * rot_freq_hz * t)
            # minor harmonics
            signal += 0.1 * vibration_level * np.sin(2.0 * np.pi * (2.0 * rot_freq_hz) * t)
            
        elif defect_type == "desalineacion":
            # Misalignment: 2x RPM and 3x RPM are dominant, 1x RPM also visible
            signal += 0.5 * vibration_level * np.sin(2.0 * np.pi * rot_freq_hz * t)
            signal += 1.5 * vibration_level * np.sin(2.0 * np.pi * (2.0 * rot_freq_hz) * t)
            signal += 0.8 * vibration_level * np.sin(2.0 * np.pi * (3.0 * rot_freq_hz) * t)
            
        elif defect_type == "rodamiento":
            # Bearing defect: High frequency peaks (e.g. BPFO at 4.2x RPM and BPFI at 5.8x RPM)
            # PLUS periodic impacts (shock waves) modeled as decaying exponentials
            bpfo = 4.25 * rot_freq_hz
            bpfi = 5.82 * rot_freq_hz
            
            signal += 0.3 * vibration_level * np.sin(2.0 * np.pi * rot_freq_hz * t)
            
            # Shock waves repeated at BPFO rate
            impact_period = 1.0 / bpfo
            impact_times = np.arange(0, duration_seconds, impact_period)
            
            for ti in impact_times:
                # decaying carrier frequency
                decay = np.exp(-150.0 * (t - ti)) * (t >= ti)
                signal += 1.8 * vibration_level * np.sin(2.0 * np.pi * 350.0 * t) * decay
                
        elif defect_type == "cavitacion":
            # Cavitation: Broadband white noise in high frequencies (e.g., 200 - 800 Hz)
            # plus slight pressure pulsations at blade pass frequency BPF (e.g., 5 blades = 5x RPM)
            bpf = 5.0 * rot_freq_hz
            signal += 0.4 * vibration_level * np.sin(2.0 * np.pi * rot_freq_hz * t)
            signal += 0.6 * vibration_level * np.sin(2.0 * np.pi * bpf * t)
            
            # broadband high-frequency energy
            broadband_noise = np.random.normal(0, 0.4 * vibration_level, n_samples)
            # filter to high frequencies (crude highpass filter)
            nyquist = sampling_rate / 2.0
            # Simulating high frequency energy using noise scaled by a high frequency sine wave
            high_freq_carrier = np.sin(2.0 * np.pi * 600.0 * t) + np.sin(2.0 * np.pi * 750.0 * t)
            signal += 0.8 * vibration_level * broadband_noise * high_freq_carrier
            
        else:  # nominal state
            # Minor 1x RPM and standard noise
            signal += 0.15 * vibration_level * np.sin(2.0 * np.pi * rot_freq_hz * t)
            signal += 0.05 * vibration_level * np.sin(2.0 * np.pi * (2.0 * rot_freq_hz) * t)
            
        # Execute real-valued Fast Fourier Transform
        # rfft yields half the frequency spectrum, representing positive frequencies
        fft_amplitudes = np.abs(np.fft.rfft(signal)) / n_samples * 2.0
        fft_frequencies = np.fft.rfftfreq(n_samples, d=1.0/sampling_rate)
        
        # Extract main spectral peaks
        peaks_indices = np.argsort(fft_amplitudes)[::-1][:5]
        peaks = []
        for idx in peaks_indices:
            freq = float(fft_frequencies[idx])
            amp = float(fft_amplitudes[idx])
            if amp > 0.01:
                # Relate to defect signatures
                rel_order = freq / rot_freq_hz if rot_freq_hz > 0 else 0
                label = f"{rel_order:.2f}x RPM"
                if abs(rel_order - 1.0) < 0.05:
                    label = "1x RPM (Rotacional)"
                elif abs(rel_order - 2.0) < 0.05:
                    label = "2x RPM (Armónico / Desalineación)"
                elif abs(rel_order - 3.0) < 0.05:
                    label = "3x RPM (Desalineación)"
                elif abs(rel_order - 5.0) < 0.05:
                    label = "5x RPM (Frecuencia de Alabes - BPF)"
                elif freq > 300.0:
                    label = "Alta Frecuencia (Rodamiento/Cavitación)"
                    
                peaks.append({
                    "frequency_hz": freq,
                    "amplitude_mms": amp,
                    "label": label
                })
                
        return {
            "defect_type": defect_type,
            "rpm": rpm,
            "vibration_level": vibration_level,
            "sampling_rate": sampling_rate,
            "time_series": {
                "time": t.tolist()[:400],  # send first 400 points to keep payload small
                "amplitude": signal.tolist()[:400]
            },
            "fft_spectrum": {
                "frequencies": fft_frequencies.tolist(),
                "amplitudes": fft_amplitudes.tolist()
            },
            "spectral_peaks": sorted(peaks, key=lambda x: x["frequency_hz"])
        }
