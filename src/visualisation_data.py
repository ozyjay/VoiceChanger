from dataclasses import dataclass

import numpy as np

from audio_effects import fft_data, waveform_data


@dataclass(frozen=True)
class AudioSeries:
    waveform_times: np.ndarray
    waveform_amplitudes: np.ndarray
    waveform_limit: float
    fft_freqs: np.ndarray
    fft_magnitudes: np.ndarray
    fft_display_magnitudes: np.ndarray
    dominant_frequency: float
    peak_amplitude: float


@dataclass(frozen=True)
class VisualisationData:
    effect_name: str
    samplerate: int
    duration_seconds: float
    max_frequency: float
    waveform_limit: float
    display_gain: float
    difference_waveform_amplitudes: np.ndarray
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
    waveform_limit = _waveform_limit(original_audio, processed_audio)
    original = _build_series(original_audio, samplerate, max_frequency, waveform_points, waveform_limit)
    processed = None
    if processed_audio is not None:
        processed = _build_series(processed_audio, samplerate, max_frequency, waveform_points, waveform_limit)

    difference = _difference_waveform(original, processed)

    return VisualisationData(
        effect_name=effect_name,
        samplerate=int(samplerate),
        duration_seconds=_duration_seconds(original_audio, samplerate),
        max_frequency=float(max_frequency),
        waveform_limit=waveform_limit,
        display_gain=_display_gain(waveform_limit),
        difference_waveform_amplitudes=difference,
        original=original,
        processed=processed,
    )


def _build_series(audio_data, samplerate, max_frequency, waveform_points, waveform_limit):
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
        waveform_limit=waveform_limit,
        fft_freqs=freqs,
        fft_magnitudes=magnitudes,
        fft_display_magnitudes=_db_display_magnitudes(magnitudes),
        dominant_frequency=dominant_frequency,
        peak_amplitude=peak_amplitude,
    )


def _duration_seconds(audio_data, samplerate):
    if audio_data is None:
        return 0.0
    return len(audio_data) / float(samplerate)


def _waveform_limit(original_audio, processed_audio):
    peaks = [_peak(original_audio)]
    if processed_audio is not None:
        peaks.append(_peak(processed_audio))

    peak = max(peaks)
    if peak <= 0:
        return 0.05
    return float(max(0.05, min(1.0, peak * 1.2)))


def _peak(audio_data):
    if audio_data is None:
        return 0.0
    audio = np.asarray(audio_data, dtype=np.float32)
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def _display_gain(waveform_limit):
    if waveform_limit <= 0.05:
        return 1.0
    return float(1.0 / waveform_limit)


def _difference_waveform(original, processed):
    if processed is None:
        return np.zeros_like(original.waveform_amplitudes)

    count = min(len(original.waveform_amplitudes), len(processed.waveform_amplitudes))
    difference = np.zeros_like(original.waveform_amplitudes)
    difference[:count] = processed.waveform_amplitudes[:count] - original.waveform_amplitudes[:count]
    return difference


def _db_display_magnitudes(magnitudes):
    if len(magnitudes) == 0:
        return magnitudes

    peak = float(np.max(magnitudes))
    if peak <= 0:
        return np.zeros_like(magnitudes)

    floor_db = -50.0
    db_values = 20.0 * np.log10(np.maximum(magnitudes / peak, 10 ** (floor_db / 20.0)))
    return ((db_values - floor_db) / -floor_db).astype(np.float32)
