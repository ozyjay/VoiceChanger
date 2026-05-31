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


if __name__ == "__main__":
    unittest.main()
