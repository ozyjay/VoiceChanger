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

- Python 3.11+
- PySide6
- NumPy
- sounddevice

The project has a standard `pyproject.toml`, but no lockfile or project virtual environment is currently checked in.

## Useful Commands

Compile-check the Python files:

```bash
python3 -m py_compile src/main.py src/gui.py
```

Run the GUI:

```bash
python3 src/main.py
```

If using Poetry later:

```bash
poetry install
poetry run python src/main.py
```

## Development Notes

- Keep edits small and verify immediately.
- Prefer adding behaviour in stages: UI wiring, audio I/O, effects, visualisation, packaging.
- Avoid deleting `src/gui.py` unless the project entry-point structure is deliberately changed.
- Review `docs/ROADMAP.md` before adding larger features.
