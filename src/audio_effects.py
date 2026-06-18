import numpy as np


EFFECT_NAMES = ("Normal", "Chipmunk", "Giant", "Robot", "Radio", "Alien", "Echo")


def apply_effect(audio_data, effect_name, samplerate):
    audio = _as_audio_array(audio_data)

    if effect_name == "Normal":
        processed = audio.copy()
    elif effect_name == "Chipmunk":
        processed = _frequency_shift(audio, 1.45)
    elif effect_name == "Giant":
        processed = _frequency_shift(audio, 0.68)
    elif effect_name == "Robot":
        processed = _robot(audio, samplerate)
    elif effect_name == "Radio":
        processed = _radio(audio, samplerate)
    elif effect_name == "Alien":
        processed = _alien(audio, samplerate)
    elif effect_name == "Echo":
        processed = _echo(audio, samplerate)
    else:
        processed = audio.copy()

    return _limit(processed).astype(np.float32)


def prepare_playback_audio(audio_data, samplerate=44100, ceiling=0.95):
    audio = _as_audio_array(audio_data)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= 0:
        return audio.astype(np.float32)

    ceiling = float(max(0.1, min(1.0, ceiling)))
    scaled = audio / max(peak, ceiling)
    limited = np.tanh(scaled * 1.15) / np.tanh(1.15)
    prepared = limited * ceiling

    fade_samples = min(int(float(samplerate) * 0.01), len(prepared) // 4)
    if fade_samples >= 2:
        fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32).reshape(-1, 1)
        prepared[:fade_samples] *= fade_in
        prepared[-fade_samples:] *= fade_in[::-1]

    return prepared.astype(np.float32)


def waveform_data(audio_data, samplerate, max_points=1000):
    audio = _mono(_as_audio_array(audio_data))
    if len(audio) == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    point_count = min(max(1, int(max_points)), len(audio))
    indices = np.linspace(0, len(audio) - 1, point_count).astype(int)
    times = indices.astype(np.float32) / float(samplerate)
    amplitudes = audio[indices].astype(np.float32)
    return times, amplitudes


def fft_data(audio_data, samplerate):
    audio = _mono(_as_audio_array(audio_data))
    if len(audio) == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    window = np.hanning(len(audio)).astype(np.float32)
    spectrum = np.fft.rfft(audio * window)
    magnitudes = np.abs(spectrum).astype(np.float32)
    peak = float(np.max(magnitudes)) if len(magnitudes) else 0.0
    if peak > 0:
        magnitudes = magnitudes / peak
    freqs = np.fft.rfftfreq(len(audio), d=1 / samplerate).astype(np.float32)
    return freqs, magnitudes


def _as_audio_array(audio_data):
    audio = np.asarray(audio_data, dtype=np.float32)
    if audio.ndim == 1:
        return audio.reshape(-1, 1)
    if audio.ndim == 2:
        return audio.copy()
    raise ValueError("audio_data must be a 1D or 2D array")


def _mono(audio):
    if audio.ndim == 1:
        return audio
    return np.mean(audio, axis=1)


def _frequency_shift(audio, factor):
    shifted_channels = [_resample_pitch_channel(audio[:, channel], factor) for channel in range(audio.shape[1])]
    return np.stack(shifted_channels, axis=1)


def _resample_pitch_channel(samples, factor):
    original_length = len(samples)
    if original_length == 0:
        return samples.astype(np.float32)

    new_length = max(1, int(round(original_length / factor)))
    source_positions = np.arange(new_length, dtype=np.float32) * factor
    source_positions = np.clip(source_positions, 0, original_length - 1)
    resampled = np.interp(source_positions, np.arange(original_length), samples).astype(np.float32)

    if new_length >= original_length:
        return resampled[:original_length]

    output = np.zeros(original_length, dtype=np.float32)
    output[:new_length] = resampled
    return output


def _robot(audio, samplerate):
    t = np.arange(len(audio), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    modulator = np.cos(2 * np.pi * 30.0 * t)
    return (audio * 0.45) + (audio * modulator * 0.75)


def _radio(audio, samplerate):
    filtered_channels = []
    freqs = np.fft.rfftfreq(len(audio), d=1 / samplerate)
    band = (freqs >= 300) & (freqs <= 3200)

    for channel in range(audio.shape[1]):
        spectrum = np.fft.rfft(audio[:, channel])
        spectrum[~band] *= 0.08
        spectrum[band] *= 1.25
        filtered_channels.append(np.fft.irfft(spectrum, n=len(audio)).astype(np.float32))

    filtered = np.stack(filtered_channels, axis=1)
    return np.tanh(filtered * 1.8).astype(np.float32)


def _alien(audio, samplerate):
    pitched = _frequency_shift(audio, 1.22)
    t = np.arange(len(audio), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    shimmer = 0.75 + (0.35 * np.sin(2 * np.pi * 70.0 * t))
    return _echo(pitched * shimmer, samplerate, delay_seconds=0.09, feedback=0.28)


def _echo(audio, samplerate, delay_seconds=0.16, feedback=0.42):
    delay_samples = max(1, int(samplerate * delay_seconds))
    output = audio.copy()

    if delay_samples < len(audio):
        output[delay_samples:] += audio[:-delay_samples] * feedback

    return output


def _limit(audio):
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        return audio / peak
    return np.clip(audio, -1.0, 1.0)
