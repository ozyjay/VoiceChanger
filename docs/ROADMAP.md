# VoiceChanger Roadmap

This roadmap keeps the project moving in small, testable stages.

## Stage 1: Stabilise The GUI Shell

- Keep `src/main.py` as the runnable entry point.
- Decide whether `src/gui.py` remains a compatibility shim or becomes the launcher.
- Convert important widgets to instance attributes when they need signal wiring.
- Connect buttons and dropdown changes to placeholder methods.
- Compile-check after each edit.

## Stage 2: Add Audio Recording And Playback

- Choose an audio I/O library, likely `sounddevice`.
- Record short clips into a NumPy array.
- Store sample rate and recorded audio on the main window.
- Add clear user feedback for empty recordings and playback state.
- Keep recording length bounded for Open Day reliability.

## Stage 3: Implement Simple Effects

Start with effects that are easy to explain and reliable live:

- Normal: no processing.
- Echo: delayed, decayed copy of the signal.
- Radio: band-pass style filtering or simple EQ approximation.
- Robot: amplitude modulation or quantisation-style effect.

Then consider more complex effects:

- Chipmunk: pitch shift up.
- Giant: pitch shift down.
- Alien: modulation plus pitch or delay effects.

## Stage 4: Add Waveform And FFT Visualisation

- Replace the placeholder label with a dedicated visualisation widget.
- Show the recorded waveform.
- Show an FFT magnitude plot for the current audio.
- Keep drawing lightweight enough for live demos.

## Stage 5: Improve Project Packaging

- Fix or confirm dependencies in `pyproject.toml`.
- Add a lockfile once dependencies are chosen.
- Decide between Poetry-managed environments and a simple `.venv` workflow.
- Add a short setup section for demo operators.

## Stage 6: Demo Polish

- Add friendly status labels.
- Disable buttons when actions are not available.
- Add short default recording duration.
- Include simple error messages for missing microphone or playback device.
- Test on the actual Open Day machine.
