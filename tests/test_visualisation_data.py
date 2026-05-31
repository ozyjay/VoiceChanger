import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from audio_effects import apply_effect
from visualisation_data import build_visualisation_data


def sine_wave(frequency, samplerate=12000, seconds=1.0, amplitude=0.7):
    t = np.arange(int(samplerate * seconds), dtype=np.float32) / samplerate
    return (amplitude * np.sin(2 * np.pi * frequency * t)).reshape(-1, 1)


class VisualisationDataTests(unittest.TestCase):
    def test_builds_original_and_processed_series_for_teaching_comparison(self):
        samplerate = 12000
        original = sine_wave(300, samplerate=samplerate)
        processed = apply_effect(original, "Chipmunk", samplerate=samplerate)

        data = build_visualisation_data(original, processed, samplerate, "Chipmunk")

        self.assertEqual(data.effect_name, "Chipmunk")
        self.assertAlmostEqual(data.duration_seconds, 1.0, places=3)
        self.assertEqual(len(data.original.waveform_times), 400)
        self.assertEqual(len(data.original.waveform_amplitudes), 400)
        self.assertEqual(len(data.processed.waveform_times), 400)
        self.assertEqual(len(data.processed.waveform_amplitudes), 400)

    def test_limits_fft_to_voice_band(self):
        samplerate = 12000
        original = sine_wave(440, samplerate=samplerate)
        processed = apply_effect(original, "Robot", samplerate=samplerate)

        data = build_visualisation_data(original, processed, samplerate, "Robot", max_frequency=5000)

        self.assertLessEqual(float(np.max(data.original.fft_freqs)), 5000.0)
        self.assertLessEqual(float(np.max(data.processed.fft_freqs)), 5000.0)
        self.assertGreater(len(data.original.fft_freqs), 0)
        self.assertEqual(len(data.original.fft_freqs), len(data.original.fft_magnitudes))

    def test_reports_distinct_dominant_frequencies_for_pitch_effects(self):
        samplerate = 12000
        original = sine_wave(300, samplerate=samplerate)
        processed = apply_effect(original, "Chipmunk", samplerate=samplerate)

        data = build_visualisation_data(original, processed, samplerate, "Chipmunk")

        self.assertAlmostEqual(data.original.dominant_frequency, 300, delta=2)
        self.assertGreater(data.processed.dominant_frequency, data.original.dominant_frequency + 100)

    def test_handles_missing_processed_audio_without_crashing(self):
        samplerate = 12000
        original = sine_wave(220, samplerate=samplerate)

        data = build_visualisation_data(original, None, samplerate, "Normal")

        self.assertEqual(data.effect_name, "Normal")
        self.assertIsNone(data.processed)
        self.assertAlmostEqual(data.original.dominant_frequency, 220, delta=2)

    def test_low_amplitude_audio_uses_honest_zoomed_waveform_limit(self):
        samplerate = 12000
        original = sine_wave(220, samplerate=samplerate, amplitude=0.08)
        processed = original * 0.5

        data = build_visualisation_data(original, processed, samplerate, "Quiet")

        self.assertGreater(data.waveform_limit, 0.08)
        self.assertLess(data.waveform_limit, 0.12)
        self.assertGreater(data.display_gain, 8.0)

    def test_original_and_processed_share_waveform_limit(self):
        samplerate = 12000
        original = sine_wave(220, samplerate=samplerate, amplitude=0.08)
        processed = sine_wave(220, samplerate=samplerate, amplitude=0.18)

        data = build_visualisation_data(original, processed, samplerate, "Louder")

        self.assertAlmostEqual(data.waveform_limit, data.processed.waveform_limit)
        self.assertAlmostEqual(data.waveform_limit, data.original.waveform_limit)
        self.assertGreater(data.waveform_limit, 0.18)
        self.assertLess(data.waveform_limit, 0.25)

    def test_difference_waveform_highlights_processed_change(self):
        samplerate = 12000
        original = sine_wave(300, samplerate=samplerate, amplitude=0.3)
        processed = apply_effect(original, "Robot", samplerate=samplerate)

        data = build_visualisation_data(original, processed, samplerate, "Robot")

        self.assertEqual(len(data.difference_waveform_amplitudes), len(data.original.waveform_amplitudes))
        self.assertGreater(float(np.max(np.abs(data.difference_waveform_amplitudes))), 0.02)

    def test_fft_display_magnitudes_lift_quieter_harmonics(self):
        samplerate = 12000
        original = sine_wave(400, samplerate=samplerate, amplitude=0.7)
        original += sine_wave(1200, samplerate=samplerate, amplitude=0.07)

        data = build_visualisation_data(original, original, samplerate, "Normal")
        raw_ratio = _magnitude_at(data.original.fft_magnitudes, data.original.fft_freqs, 1200)
        display_ratio = _magnitude_at(data.original.fft_display_magnitudes, data.original.fft_freqs, 1200)

        self.assertLess(raw_ratio, 0.2)
        self.assertGreater(display_ratio, 0.55)

    def test_silent_audio_has_safe_display_defaults(self):
        samplerate = 12000
        silence = np.zeros((samplerate, 1), dtype=np.float32)

        data = build_visualisation_data(silence, silence, samplerate, "Normal")

        self.assertEqual(data.waveform_limit, 0.05)
        self.assertEqual(data.display_gain, 1.0)
        self.assertTrue(np.all(np.isfinite(data.original.fft_display_magnitudes)))
        self.assertTrue(np.all(np.isfinite(data.difference_waveform_amplitudes)))


def _magnitude_at(magnitudes, freqs, frequency):
    return float(magnitudes[int(np.argmin(np.abs(freqs - frequency)))])


if __name__ == "__main__":
    unittest.main()
