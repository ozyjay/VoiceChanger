# VoiceChanger

Local, offline PySide6 Open Day demo for recording, transforming, playing, and visualising short voice clips.

## Current Status

The app is now a working `Voice Changer Live` demo with a playful pedalboard-style interface:

- Record a short voice clip from the microphone.
- Automatically stop recording after about 5 seconds for reliable public demos.
- Play the original clip.
- Toggle one or more effect pedals: Chipmunk, Giant, Robot, Radio, Alien, and Echo.
- Play the processed result with a dynamic button label such as `Play Normal`, `Play Echo`, or `Play Chain`.
- See the current `ACTIVE CHAIN` near the top of the window.
- Read a short plain-English `What changed?` explanation for the selected effect chain.
- Compare original and processed audio with waveform and FFT visualisations.
- Use `Reset / Next Visitor` to clear audio and return to a clean Normal voice starting state.

The demo remains local and offline. It uses `sounddevice` for microphone and speaker access, NumPy for audio processing, and PySide6 for the GUI.

## Project Layout

```text
src/
  main.py                       # Main PySide6 window and runnable entry point
  gui.py                        # Compatibility shim exposing MainWindow
  audio_effects.py              # Audio effect implementations and audio helpers
  audio_visualisation_widget.py # PySide6 waveform/FFT comparison widget
  visualisation_data.py         # Pure visualisation data preparation
tests/
  test_audio_effects.py
  test_project_setup.py
  test_visualisation_data.py
```

## Requirements

- Python 3.12.13 via pyenv
- Poetry
- PySide6
- NumPy
- sounddevice

The project has a standard `pyproject.toml`, a `poetry.lock` file, and a `.python-version` file for pyenv. Poetry creates its virtual environment outside the repo by default.

Use the pinned Python version:

```bash
pyenv install 3.12.13
pyenv local 3.12.13
python --version
```

## Useful Commands

Install dependencies:

```bash
./scripts/setup.sh
```

Run tests and compile checks:

```bash
./scripts/test.sh
```

Run the GUI:

```bash
./scripts/run.sh
```

## Demo Operator Flow

1. Run setup with `./scripts/setup.sh`.
2. Run tests with `./scripts/test.sh`.
3. Run the app with `./scripts/run.sh`.
4. Ask the visitor to press `Record` and say a short phrase. Recording auto-stops after about 5 seconds.
5. Toggle one or more bright effect pedals.
6. Use `Play Original` and the processed playback button to compare the voices.
7. Point out the `ACTIVE CHAIN`, `What changed?` panel, waveform, and FFT comparison.
8. Press `Reset / Next Visitor` before the next visitor.

## Development Notes

- Keep edits small and verify immediately.
- Preserve the PySide6 desktop direction.
- Keep the audio effects engine local and offline.
- Preserve multi-effect stacking.
- Avoid deleting `src/gui.py` unless the entry-point structure is deliberately changed.
- Review `docs/ROADMAP.md` before adding larger features.
