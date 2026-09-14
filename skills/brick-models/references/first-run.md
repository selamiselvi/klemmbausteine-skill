# First-run checks

## Astra before design

This project's design workflow targets OpenAI GPT-6 Astra (`gpt-6-astra`). Treat that as the project's quality recommendation, not evidence that every other model fails or that a skill can change its host model.

1. Use an exact current-model identity only if the host explicitly exposes it in trusted session/turn metadata or a documented tool for the current session. Pass it to `python scripts/preflight.py --active-model MODEL_ID`. A model list only proves availability. Global settings, a default model, filenames, installed programs, generic self-descriptions such as “GPT-6”, and old chat logs do not prove the current model. Do not search private session databases or credentials to infer it.
2. If the identity is unavailable, run `python scripts/preflight.py` without a model. Present its single question in the user's language. If another model is identified, present its switch request. Wait for the user's answer before model design, even in automatic intake mode. “I will switch” is pending, not confirmation. Reuse an explicit current-session confirmation with `--confirmed-astra`; do not repeat the question on every revision. Recheck if the host reports a model change.
3. Do not change global configuration, start a new agent, or claim to switch the active model. The user selects Astra in their host. If they explicitly prefer to continue with another model after the notice, use `--accept-other` and proceed without claiming Astra-level results. No response is not an override.

The helper evaluates supplied evidence and standardizes the question; it cannot detect the host model itself. Codex skills do not supply a portable self-introspection interface. See [Codex skills](https://learn.chatgpt.com/docs/build-skills) and [App Server model/session metadata](https://learn.chatgpt.com/docs/app-server). Documentation and available host capabilities were checked in September 2026; do not invent APIs on other hosts.

## Python and Blender

Check Python 3.11+ and run `python scripts/brick.py doctor` with an available interpreter. A missing import is also a setup-needed result. If dependencies or Blender are missing, announce the required setup briefly and run:

```sh
python3 scripts/setup_runtime.py
```

The helper uses an existing Blender where possible, creates an isolated Python environment in the user's cache, and otherwise downloads a checksum-pinned official Blender 5.2.0 package. It prints the Python and Blender executable paths. Use those exact paths for subsequent commands; pass `--blender` on builds when needed. Do not install dependencies into the skill checkout or the user's global Python.

The normal user-space setup is part of fulfilling a model-generation request when the host's permissions allow it. Announce the approximately 350–410 MB Blender download before starting; do not add a redundant permission question when already authorized. If the host requires approval, the user restricted installations/downloads, or administrator privileges are needed, honor that boundary. Never use sudo, bypass Gatekeeper, remove quarantine flags, modify global PATH, or overwrite an existing Blender to avoid a prompt. If Python itself is missing, explain the prerequisite and use the host's approved installation flow; the Python helper cannot bootstrap its own interpreter.

Default locations are computed from the current user's OS cache directory, never from a maintainer's path. `--runtime-dir` or `BRICK_MODELS_RUNTIME` can select another directory outside repositories. `--portable` requests an isolated Blender even when one is already installed, useful for first-run testing. A custom directory's Blender must be passed explicitly or selected through `BRICK_MODELS_RUNTIME`.

Automatic packages cover macOS Apple Silicon, Linux x64, and Windows x64/ARM64. Unsupported systems (including Intel Macs) receive a clear error and can use a compatible manually installed official Blender via `BLENDER_BIN` or `--blender`. This is not a promise that every GPU/OS supports rendering. Download or setup failure stops rendering; report the exact problem. Do not silently substitute a flat image generator.

The helper verifies the official archive SHA-256 before extraction, removes download/mount staging on completion, and leaves the reusable runtime in the cache. Run `doctor` again using the returned Python and `BLENDER_BIN`, then validate and render the actual model. A successful version command alone is not a rendering test. Official packages: [Blender downloads](https://download.blender.org/release/Blender5.2/).
