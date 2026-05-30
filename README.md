# VoiceChanger

Local Open Day demo for recording, transforming, playing, and visualising voice audio.

## Current Status

This project is currently a PySide6 GUI demo in early implementation. It has:

- A main window titled `Open Day Voice Effects Demo`
- Buttons for recording, playing the original audio, and playing filtered audio
- A dropdown of planned effects: Normal, Chipmunk, Giant, Robot, Radio, Alien, Echo
- Basic microphone recording and playback through `sounddevice`
- Early placeholder audio effects, with Echo partially implemented
- A placeholder area for future waveform and FFT visualisation

The visualisation logic and most effects are not implemented yet.

## Project Layout

```text
src/
  main.py   # Main PySide6 window and runnable entry point
  gui.py    # Compatibility shim exposing MainWindow
```

## Requirements

- Python 3.12.13 via pyenv
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

## Development Notes

- Keep edits small and verify immediately.
- Prefer adding behaviour in stages: UI wiring, audio I/O, effects, visualisation, packaging.
- Avoid deleting `src/gui.py` unless the project entry-point structure is deliberately changed.
- Review `docs/ROADMAP.md` before adding larger features.
