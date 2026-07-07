import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from audio_effects import EFFECT_NAMES, apply_effect, fft_data, prepare_playback_audio, waveform_data


def sine_wave(frequency, samplerate=8000, seconds=1.0, amplitude=0.7):
    t = np.arange(int(samplerate * seconds), dtype=np.float32) / samplerate
    return (amplitude * np.sin(2 * np.pi * frequency * t)).reshape(-1, 1)


def dominant_frequency(samples, samplerate):
    mono = np.asarray(samples, dtype=np.float32).reshape(-1)
    freqs = np.fft.rfftfreq(len(mono), d=1 / samplerate)
    magnitudes = np.abs(np.fft.rfft(mono))
    magnitudes[0] = 0
    return freqs[int(np.argmax(magnitudes))]


def magnitude_at(samples, samplerate, frequency):
    mono = np.asarray(samples, dtype=np.float32).reshape(-1)
    freqs = np.fft.rfftfreq(len(mono), d=1 / samplerate)
    magnitudes = np.abs(np.fft.rfft(mono))
    return magnitudes[int(np.argmin(np.abs(freqs - frequency)))]


def mean_abs_change(processed, original):
    count = min(len(processed), len(original))
    return float(np.mean(np.abs(processed[:count] - original[:count])))


class AudioEffectsTests(unittest.TestCase):
    def test_chipmunk_raises_dominant_frequency_without_changing_clip_length(self):
        audio = sine_wave(220)

        processed = apply_effect(audio, "Chipmunk", samplerate=8000)

        self.assertEqual(processed.shape, audio.shape)
        self.assertGreater(dominant_frequency(processed, 8000), 280)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_chipmunk_keeps_single_transient_from_becoming_echo_train(self):
        samplerate = 8000
        audio = np.zeros((samplerate, 1), dtype=np.float32)
        burst = sine_wave(440, samplerate=samplerate, seconds=0.05, amplitude=0.7)
        audio[3600:3600 + len(burst)] = burst

        processed = apply_effect(audio, "Chipmunk", samplerate=samplerate)

        envelope = np.abs(processed.reshape(-1))
        active = envelope > (float(np.max(envelope)) * 0.2)
        active_indices = np.flatnonzero(active)
        active_span = int(active_indices[-1] - active_indices[0])

        self.assertLess(active_span, 500)

    def test_pitch_shortening_fades_into_padded_tail_without_hard_click(self):
        samplerate = 8000
        audio = np.ones((samplerate, 1), dtype=np.float32) * 0.5

        processed = apply_effect(audio, "Chipmunk", samplerate=samplerate)
        largest_step = float(np.max(np.abs(np.diff(processed.reshape(-1)))))

        self.assertLess(largest_step, 0.08)

    def test_pitch_shortening_stays_smooth_inside_effect_chains(self):
        samplerate = 8000
        audio = sine_wave(220, samplerate=samplerate, seconds=1.0, amplitude=0.45)
        processed = audio
        for effect_name in ("Chipmunk", "Robot", "Echo"):
            processed = apply_effect(processed, effect_name, samplerate=samplerate)

        largest_step = float(np.max(np.abs(np.diff(processed.reshape(-1)))))

        self.assertLess(largest_step, 0.25)

    def test_giant_lowers_dominant_frequency_without_cutting_off_later_words(self):
        audio = sine_wave(260)

        processed = apply_effect(audio, "Giant", samplerate=8000)

        self.assertGreater(len(processed), len(audio))
        self.assertLess(dominant_frequency(processed, 8000), 210)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_robot_adds_audible_modulation_and_stays_bounded(self):
        audio = sine_wave(440, amplitude=0.5)

        processed = apply_effect(audio, "Robot", samplerate=8000)

        self.assertEqual(processed.shape, audio.shape)
        self.assertGreater(float(np.mean(np.abs(processed - audio))), 0.05)
        self.assertGreater(magnitude_at(processed, 8000, 470), magnitude_at(audio, 8000, 470) * 10)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_radio_emphasises_speech_band_over_low_and_very_high_content(self):
        samplerate = 8000
        audio = sine_wave(120, samplerate=samplerate, amplitude=0.4)
        audio += sine_wave(1000, samplerate=samplerate, amplitude=0.4)
        audio += sine_wave(3800, samplerate=samplerate, amplitude=0.4)

        processed = apply_effect(audio, "Radio", samplerate=samplerate)

        self.assertEqual(processed.shape, audio.shape)
        speech = magnitude_at(processed, samplerate, 1000)
        low = magnitude_at(processed, samplerate, 120)
        high = magnitude_at(processed, samplerate, 3800)
        self.assertGreater(speech, low * 3)
        self.assertGreater(speech, high * 3)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_echo_adds_delayed_signal_without_clipping(self):
        samplerate = 8000
        audio = np.zeros((samplerate // 2, 1), dtype=np.float32)
        audio[0, 0] = 1.0

        processed = apply_effect(audio, "Echo", samplerate=samplerate)

        self.assertEqual(len(processed), len(audio) + int(samplerate * 0.16))
        self.assertAlmostEqual(float(processed[0, 0]), 1.0, places=5)
        self.assertGreater(float(processed[int(samplerate * 0.16), 0]), 0.2)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_alien_combines_pitch_and_modulation(self):
        audio = sine_wave(300, amplitude=0.5)

        processed = apply_effect(audio, "Alien", samplerate=8000)

        self.assertGreater(len(processed), len(audio))
        self.assertGreater(mean_abs_change(processed, audio), 0.05)
        self.assertNotAlmostEqual(dominant_frequency(processed, 8000), 300, delta=10)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_wild_effects_are_registered_and_safe(self):
        audio = sine_wave(330, amplitude=0.45)

        for effect_name in ("Megaphone", "Underwater", "Vibrato", "Choir", "Monster", "Cave"):
            with self.subTest(effect_name=effect_name):
                self.assertIn(effect_name, EFFECT_NAMES)
                processed = apply_effect(audio, effect_name, samplerate=8000)
                self.assertEqual(processed.shape[1], audio.shape[1])
                self.assertGreaterEqual(len(processed), len(audio))
                self.assertEqual(processed.dtype, np.float32)
                self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)
                self.assertGreater(mean_abs_change(processed, audio), 0.005)

    def test_megaphone_emphasises_speech_band_and_adds_drive(self):
        samplerate = 8000
        audio = sine_wave(120, samplerate=samplerate, amplitude=0.25)
        audio += sine_wave(1000, samplerate=samplerate, amplitude=0.25)
        audio += sine_wave(3600, samplerate=samplerate, amplitude=0.25)

        processed = apply_effect(audio, "Megaphone", samplerate=samplerate)

        speech = magnitude_at(processed, samplerate, 1000)
        low = magnitude_at(processed, samplerate, 120)
        high = magnitude_at(processed, samplerate, 3600)
        self.assertGreater(speech, low * 4)
        self.assertGreater(speech, high * 4)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_underwater_muffles_high_frequencies(self):
        samplerate = 8000
        audio = sine_wave(300, samplerate=samplerate, amplitude=0.35)
        audio += sine_wave(2400, samplerate=samplerate, amplitude=0.35)

        processed = apply_effect(audio, "Underwater", samplerate=samplerate)

        low = magnitude_at(processed, samplerate, 300)
        high = magnitude_at(processed, samplerate, 2400)
        self.assertGreater(low, high * 5)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_vibrato_adds_pitch_wobble_sidebands(self):
        samplerate = 8000
        audio = sine_wave(440, samplerate=samplerate, amplitude=0.45)

        processed = apply_effect(audio, "Vibrato", samplerate=samplerate)

        self.assertGreater(magnitude_at(processed, samplerate, 445), magnitude_at(audio, samplerate, 445) * 2)
        self.assertGreater(float(np.mean(np.abs(processed - audio))), 0.02)

    def test_choir_layers_delayed_copies(self):
        samplerate = 8000
        audio = np.zeros((samplerate // 2, 1), dtype=np.float32)
        audio[0, 0] = 0.8

        processed = apply_effect(audio, "Choir", samplerate=samplerate)

        self.assertGreater(float(processed[int(samplerate * 0.018), 0]), 0.05)
        self.assertGreater(float(processed[int(samplerate * 0.034), 0]), 0.05)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_monster_lowers_pitch_and_adds_growl(self):
        audio = sine_wave(300, amplitude=0.45)

        processed = apply_effect(audio, "Monster", samplerate=8000)

        self.assertGreater(len(processed), len(audio))
        self.assertLess(dominant_frequency(processed, 8000), 210)
        self.assertGreater(mean_abs_change(processed, audio), 0.05)

    def test_cave_adds_long_echoes(self):
        samplerate = 8000
        audio = np.zeros((samplerate, 1), dtype=np.float32)
        audio[0, 0] = 0.8
        audio[-1, 0] = 0.8

        processed = apply_effect(audio, "Cave", samplerate=samplerate)

        self.assertEqual(len(processed), len(audio) + int(samplerate * 0.36))
        self.assertAlmostEqual(float(processed[0, 0]), 0.8, places=5)
        self.assertGreater(float(processed[int(samplerate * 0.12), 0]), 0.2)
        self.assertGreater(float(processed[int(samplerate * 0.24), 0]), 0.1)
        self.assertGreater(float(processed[len(audio) - 1 + int(samplerate * 0.12), 0]), 0.2)
        self.assertLessEqual(float(np.max(np.abs(processed))), 1.0)

    def test_waveform_data_downsamples_to_requested_point_count(self):
        audio = np.linspace(-1, 1, 1000, dtype=np.float32).reshape(-1, 1)

        times, amplitudes = waveform_data(audio, samplerate=1000, max_points=100)

        self.assertEqual(len(times), 100)
        self.assertEqual(len(amplitudes), 100)
        self.assertAlmostEqual(float(times[-1]), 0.999, places=3)
        self.assertAlmostEqual(float(amplitudes[0]), -1.0, places=3)

    def test_fft_data_reports_dominant_frequency_peak(self):
        audio = sine_wave(440, samplerate=8000)

        freqs, magnitudes = fft_data(audio, samplerate=8000)

        self.assertAlmostEqual(float(freqs[int(np.argmax(magnitudes))]), 440, delta=2)
        self.assertAlmostEqual(float(np.max(magnitudes)), 1.0, places=5)

    def test_prepare_playback_audio_adds_headroom_for_hot_audio(self):
        audio = np.array([[-1.4], [-0.4], [0.0], [0.4], [1.6]], dtype=np.float32)

        prepared = prepare_playback_audio(audio)

        self.assertEqual(prepared.shape, audio.shape)
        self.assertEqual(prepared.dtype, np.float32)
        self.assertLessEqual(float(np.max(np.abs(prepared))), 0.95)
        self.assertGreater(float(prepared[-1, 0]), float(prepared[3, 0]))
        self.assertLess(float(prepared[0, 0]), float(prepared[1, 0]))

    def test_prepare_playback_audio_fades_edges_to_prevent_clicks(self):
        samplerate = 8000
        audio = np.ones((samplerate, 1), dtype=np.float32) * 0.4

        prepared = prepare_playback_audio(audio, samplerate=samplerate)

        self.assertAlmostEqual(float(prepared[0, 0]), 0.0, places=5)
        self.assertLess(float(prepared[1, 0]), float(prepared[100, 0]))
        self.assertAlmostEqual(float(prepared[-1, 0]), 0.0, places=5)
        self.assertLess(float(prepared[-2, 0]), float(prepared[-101, 0]))


if __name__ == "__main__":
    unittest.main()
