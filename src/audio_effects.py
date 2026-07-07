import numpy as np


EFFECT_NAMES = (
    "Normal",
    "Chipmunk",
    "Giant",
    "Robot",
    "Radio",
    "Alien",
    "Echo",
    "Megaphone",
    "Underwater",
    "Vibrato",
    "Choir",
    "Monster",
    "Cave",
)


def apply_effect(audio_data, effect_name, samplerate):
    audio = _as_audio_array(audio_data)

    if effect_name == "Normal":
        processed = audio.copy()
    elif effect_name == "Chipmunk":
        processed = _frequency_shift(audio, 1.45, samplerate, preserve_length=True)
    elif effect_name == "Giant":
        processed = _frequency_shift(audio, 0.68, samplerate)
    elif effect_name == "Robot":
        processed = _robot(audio, samplerate)
    elif effect_name == "Radio":
        processed = _radio(audio, samplerate)
    elif effect_name == "Alien":
        processed = _alien(audio, samplerate)
    elif effect_name == "Echo":
        processed = _echo(audio, samplerate)
    elif effect_name == "Megaphone":
        processed = _megaphone(audio, samplerate)
    elif effect_name == "Underwater":
        processed = _underwater(audio, samplerate)
    elif effect_name == "Vibrato":
        processed = _vibrato(audio, samplerate)
    elif effect_name == "Choir":
        processed = _choir(audio, samplerate)
    elif effect_name == "Monster":
        processed = _monster(audio, samplerate)
    elif effect_name == "Cave":
        processed = _cave(audio, samplerate)
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


def _frequency_shift(audio, factor, samplerate, preserve_length=False):
    shifted_channels = [
        _resample_pitch_channel(audio[:, channel], factor, samplerate, preserve_length=preserve_length)
        for channel in range(audio.shape[1])
    ]
    return np.stack(shifted_channels, axis=1)


def _resample_pitch_channel(samples, factor, samplerate, preserve_length=False):
    original_length = len(samples)
    if original_length == 0:
        return samples.astype(np.float32)

    new_length = max(1, int(round(original_length / factor)))
    source_positions = np.arange(new_length, dtype=np.float32) * factor
    source_positions = np.clip(source_positions, 0, original_length - 1)
    resampled = np.interp(source_positions, np.arange(original_length), samples).astype(np.float32)

    if not preserve_length:
        return resampled

    if new_length >= original_length:
        return resampled[:original_length]

    output = np.zeros(original_length, dtype=np.float32)
    fade_samples = min(max(2, int(float(samplerate) * 0.015)), new_length)
    resampled[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    output[:new_length] = resampled
    return output


def _robot(audio, samplerate):
    t = np.arange(len(audio), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    modulator = np.cos(2 * np.pi * 30.0 * t)
    return (audio * 0.45) + (audio * modulator * 0.75)


def _radio(audio, samplerate):
    filtered = _fft_band_mix(audio, samplerate, low_hz=300, high_hz=3200, inside_gain=1.25, outside_gain=0.08)
    return np.tanh(filtered * 1.8).astype(np.float32)


def _fft_band_mix(audio, samplerate, low_hz=None, high_hz=None, inside_gain=1.0, outside_gain=0.0):
    filtered_channels = []
    freqs = np.fft.rfftfreq(len(audio), d=1 / samplerate)
    band = np.ones_like(freqs, dtype=bool)
    if low_hz is not None:
        band &= freqs >= float(low_hz)
    if high_hz is not None:
        band &= freqs <= float(high_hz)

    for channel in range(audio.shape[1]):
        spectrum = np.fft.rfft(audio[:, channel])
        spectrum[~band] *= outside_gain
        spectrum[band] *= inside_gain
        filtered_channels.append(np.fft.irfft(spectrum, n=len(audio)).astype(np.float32))

    return np.stack(filtered_channels, axis=1)


def _alien(audio, samplerate):
    pitched = _frequency_shift(audio, 1.22, samplerate, preserve_length=True)
    t = np.arange(len(pitched), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    shimmer = 0.75 + (0.35 * np.sin(2 * np.pi * 70.0 * t))
    return _echo(pitched * shimmer, samplerate, delay_seconds=0.09, feedback=0.28)


def _echo(audio, samplerate, delay_seconds=0.16, feedback=0.42):
    delay_samples = max(1, int(samplerate * delay_seconds))
    output = np.zeros((len(audio) + delay_samples, audio.shape[1]), dtype=np.float32)
    output[:len(audio)] += audio
    output[delay_samples:delay_samples + len(audio)] += audio * feedback
    return output


def _megaphone(audio, samplerate):
    filtered = _fft_band_mix(audio, samplerate, low_hz=450, high_hz=2800, inside_gain=1.5, outside_gain=0.05)
    return np.tanh(filtered * 2.6).astype(np.float32)


def _underwater(audio, samplerate):
    filtered = _fft_band_mix(audio, samplerate, high_hz=900, inside_gain=1.1, outside_gain=0.04)
    t = np.arange(len(audio), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    wobble = 0.68 + (0.24 * np.sin(2 * np.pi * 3.0 * t))
    return _echo(filtered * wobble, samplerate, delay_seconds=0.055, feedback=0.18)


def _vibrato(audio, samplerate):
    return _modulated_delay(audio, samplerate, rate_hz=5.2, depth_ms=7.5, base_ms=9.0)


def _choir(audio, samplerate):
    high = _frequency_shift(audio, 1.015, samplerate, preserve_length=True)
    low = _frequency_shift(audio, 0.985, samplerate, preserve_length=True)
    layer_one = _delay(high, samplerate, delay_seconds=0.018, preserve_length=True)
    layer_two = _delay(low, samplerate, delay_seconds=0.034, preserve_length=True)
    return (audio * 0.64) + (layer_one * 0.25) + (layer_two * 0.25)


def _monster(audio, samplerate):
    pitched = _frequency_shift(audio, 0.58, samplerate)
    t = np.arange(len(pitched), dtype=np.float32).reshape(-1, 1) / float(samplerate)
    growl = 0.78 + (0.28 * np.sin(2 * np.pi * 42.0 * t))
    return np.tanh(pitched * growl * 1.45).astype(np.float32)


def _cave(audio, samplerate):
    longest_delay = int(samplerate * 0.36)
    output = np.zeros((len(audio) + longest_delay, audio.shape[1]), dtype=np.float32)
    output[:len(audio)] += audio
    for delay_seconds, feedback in ((0.12, 0.34), (0.24, 0.24), (0.36, 0.16)):
        delayed = _delay(audio, samplerate, delay_seconds)
        output[:len(delayed)] += delayed * feedback
    return output


def _delay(audio, samplerate, delay_seconds, preserve_length=False):
    delay_samples = max(1, int(samplerate * delay_seconds))
    output_length = len(audio) if preserve_length else len(audio) + delay_samples
    output = np.zeros((output_length, audio.shape[1]), dtype=np.float32)
    copy_count = min(len(audio), max(0, output_length - delay_samples))
    if copy_count > 0:
        output[delay_samples:delay_samples + copy_count] = audio[:copy_count]
    return output


def _modulated_delay(audio, samplerate, rate_hz, depth_ms, base_ms):
    output = np.zeros_like(audio)
    if len(audio) == 0:
        return output

    sample_positions = np.arange(len(audio), dtype=np.float32)
    t = sample_positions / float(samplerate)
    delay_samples = (base_ms + (depth_ms * np.sin(2 * np.pi * rate_hz * t))) * float(samplerate) / 1000.0
    source_positions = np.clip(sample_positions - delay_samples, 0, len(audio) - 1)

    for channel in range(audio.shape[1]):
        output[:, channel] = np.interp(source_positions, sample_positions, audio[:, channel]).astype(np.float32)

    return output


def _limit(audio):
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1.0:
        return audio / peak
    return np.clip(audio, -1.0, 1.0)
