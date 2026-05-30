# Continue Local Model Notes

Notes from testing Continue with local Ollama models on a 64GB unified-memory Mac.

## Current Recommended Roles

| Model | Best Use | Notes |
| --- | --- | --- |
| GPT OSS 20B Agent | Primary local agent | Good tool use and stronger reasoning, but watch stopping behaviour after terminal commands. |
| Llama 3.1 8B Agent | Reliable fallback tool driver | Smaller, fast, and demonstrated reliable file creation through Continue. |
| Gemma 4 E4B Chat/Edit | Lightweight review and edit suggestions | Useful for quick project review; do not rely on it as primary agent until tool use is smoke-tested. |
| Qwen3 Coder 30B | Heavy reasoning/editing | Strong coding model, but previously leaked pseudo-tool calls in Continue Agent mode. |

## Practical Workflow

- Use GPT OSS 20B for agentic project work.
- Use Llama 3.1 8B when tool reliability matters more than reasoning depth.
- Use Gemma for quick reviews, explanations, and low-memory chat/edit tasks.
- Use Qwen3 Coder for heavier reasoning or code generation outside fragile Agent-mode tool use.
- Avoid loading multiple large models at once; check memory pressure with `ollama ps`.

## Smoke Tests For A New Agent Model

Run these before trusting a model for project edits:

1. Create a disposable file with exact contents.
2. Read the file back and summarize it.
3. Run `python3 -m py_compile src/main.py src/gui.py`.
4. Make a small exact edit with a targeted edit tool.
5. Inspect a file and make no changes when no change is needed.
6. Run a command expected to fail and report the error accurately.
7. Propose project cleanup without editing.
8. Make a controlled cleanup only after approval.

## Pass Criteria

- Continue shows real tool calls, not raw JSON or pseudo-tool text.
- File state is verified on disk.
- Terminal commands actually run when requested.
- Final answer is prose only.
- The model stops after completing the requested action.

## Prompting Tips

For small edits:

```text
Use single_find_and_replace for this small edit. After the edit, run python3 -m py_compile src/main.py src/gui.py. Summarize in prose only and stop.
```

For review-only tasks:

```text
Inspect the relevant files and propose changes, but do not edit anything yet.
```

For terminal tasks:

```text
Use run_terminal_command for shell commands. Do not claim a command ran unless the terminal tool actually ran.
```

## Configuration Notes

- Keep model context conservative at first, such as `contextLength: 32768`.
- Use lower temperatures for coding-agent reliability.
- Add `tool_use` only after the model passes basic Continue smoke tests.
- If terminal behaviour is unreliable, include a system-message reminder: `For shell commands, use run_terminal_command`.
