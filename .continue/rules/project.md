# VoiceChanger Continue Rules

Use these rules when working in the VoiceChanger repository.

## Behaviour

- Use Continue tools directly; do not print raw JSON, XML, or pseudo-tool calls.
- After tool use succeeds, summarize the result in prose and stop.
- If a terminal command is needed, use `run_terminal_command`.
- For small code edits, prefer `single_find_and_replace`.
- Reserve whole-file edit tools for deliberate rewrites.

## Project Scope

- This is a PySide6 voice effects demo.
- `src/main.py` is the current runnable entry point.
- `src/gui.py` is a compatibility shim and should not be deleted unless explicitly requested.
- The app currently has UI controls but no recording, playback, effects, or visualisation logic.

## Verification

After Python edits, run:

```bash
python3 -m py_compile src/main.py src/gui.py
```

If asked to inspect only, do not edit files unless a clear fix is requested.

## Style

- Keep responses concise and practical.
- Prefer bullets over large tables unless comparing options.
- Mention uncertainty when project facts have not been verified from files.
- Do not invent completed terminal output or file changes.
