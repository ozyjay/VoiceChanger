from dataclasses import dataclass

import numpy as np

from audio_effects import fft_data, waveform_data


@dataclass(frozen=True)
class AudioSeries:
    waveform_times: np.ndarray
    waveform_amplitudes: np.ndarray
    fft_freqs: np.ndarray
    fft_magnitudes: np.ndarray
    dominant_frequency: float
    peak_amplitude: float


@dataclass(frozen=True)
class VisualisationData:
    effect_name: str
    samplerate: int
    duration_seconds: float
    max_frequency: float
    original: AudioSeries
    processed: AudioSeries | None


def build_visualisation_data(
    original_audio,
    processed_audio,
    samplerate,
    effect_name,
    max_frequency=5000,
    waveform_points=400,
):
    original = _build_series(original_audio, samplerate, max_frequency, waveform_points)
    processed = None
    if processed_audio is not None:
        processed = _build_series(processed_audio, samplerate, max_frequency, waveform_points)

    return VisualisationData(
        effect_name=effect_name,
        samplerate=int(samplerate),
        duration_seconds=_duration_seconds(original_audio, samplerate),
        max_frequency=float(max_frequency),
        original=original,
        processed=processed,
    )


def _build_series(audio_data, samplerate, max_frequency, waveform_points):
    times, amplitudes = waveform_data(audio_data, samplerate, max_points=waveform_points)
    freqs, magnitudes = fft_data(audio_data, samplerate)
    voice_band = freqs <= max_frequency
    freqs = freqs[voice_band]
    magnitudes = magnitudes[voice_band]

    if len(magnitudes):
        dominant_frequency = float(freqs[int(np.argmax(magnitudes))])
    else:
        dominant_frequency = 0.0

    peak_amplitude = float(np.max(np.abs(amplitudes))) if len(amplitudes) else 0.0
    return AudioSeries(
        waveform_times=times,
        waveform_amplitudes=amplitudes,
        fft_freqs=freqs,
        fft_magnitudes=magnitudes,
        dominant_frequency=dominant_frequency,
        peak_amplitude=peak_amplitude,
    )


def _duration_seconds(audio_data, samplerate):
    if audio_data is None:
        return 0.0
    return len(audio_data) / float(samplerate)
