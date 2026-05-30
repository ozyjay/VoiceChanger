# Agent Instructions

These instructions apply to the whole VoiceChanger repository.

## Project Intent

VoiceChanger is a small PySide6 desktop demo for an Open Day voice effects activity. The intended workflow is:

1. Record a short voice clip.
2. Play the original clip.
3. Apply a selected voice effect.
4. Play the filtered clip.
5. Show waveform and FFT visualisations.

The current code is only a GUI scaffold, so prefer incremental implementation over broad rewrites.

## Coding Guidelines

- Keep changes focused and easy to verify.
- Preserve the existing PySide6 direction unless explicitly asked to change GUI framework.
- Prefer small refactors before adding behaviour.
- For small edits, avoid whole-file rewrites when a targeted replacement is sufficient.
- Do not delete `src/gui.py` unless the user explicitly approves the entry-point cleanup.
- Avoid adding comments that restate obvious code.

## Verification

After Python edits, run:

```bash
python3 -m py_compile src/main.py src/gui.py
```

If GUI behaviour changes, also run the app manually when practical:

```bash
python3 src/main.py
```

## Known Project Notes

- `src/main.py` is currently the runnable entry point.
- `src/gui.py` currently exposes `MainWindow` for compatibility.
- `pyproject.toml` is present, but no `poetry.lock` or project `.venv` is currently committed.
- The dependency `mpllib` may be a typo or placeholder; check before relying on it.
