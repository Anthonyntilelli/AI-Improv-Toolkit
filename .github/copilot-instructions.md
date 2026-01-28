# GitHub Copilot Instructions

These instructions summarize the essential architecture, workflows, and conventions that AI coding agents should follow to be immediately productive in this repo.

## Architecture & Roles
- Central entry: [code/main.py](code/main.py) loads validated config and dispatches by `Mode.Role`.
- Config model: [code/config/config.py](code/config/config.py) enforces MVP limits (en-US, mono-scene, 1 actor/avatar) and Ethics Mode rules (no debug, TLS required, rating ≤ pg-13, disclaimer short/full).
- Roles: `ingest` (implemented), `hearing`/`vision`/`brain`/`output`/`health_check` (stubs).
- Ingest specifics: HID buttons via `hidapi` contexts in [code/ingest/ingest.py](code/ingest/ingest.py); audio/VAD parameters from [code/ingest/internal.toml](code/ingest/internal.toml) validated by [code/ingest/_config.py](code/ingest/_config.py).

## Communication Patterns
- NATS pub/sub for control/events; subjects: `INTERFACE` (buttons) and `health.<service>` (heartbeats). mTLS by default using certs in [secrets/pki](secrets/pki).
- Audio path uses TLS-wrapped TCP with framed messages: 4B BE uint32 JSON length → JSON metadata (utf-8) → 4B BE uint32 audio length → raw PCM int16. Required audio format: 16kHz, mono, S16_LE; default chunk 250 ms; VAD frames 10/20/30 ms with start/continuation/end semantics.

## Config & Ethics
- Load config once with `generate_config(path)`; use `config.Mode` to gate logging and behavior.
- Ethics Mode on: deny debug, force TLS (`Network.Use_tls=True`), restrict rating/disclaimer, avoid persistence/logging.
- Button config must match avatar counts; validators enforce counts for `Buttons.Avatars` and `AI.Avatars`.

## Dev Workflow
- Python 3.14+ with deps in [code/pyproject.toml](code/pyproject.toml) (`pydantic`, `nats-py`, `numpy`, `sounddevice`, `webrtcvad`).
- Lint/type-check: `ruff` and `mypy` (strict) via pre-commit; respect existing style and avoid unrelated refactors.
- Quick run (uses sample config):
	```bash
	python -m code.main
	# or from repo root
	python code/main.py
	```


## Deployment & Infra
- Ansible roles for `nats`, `ingest`, `base`, `physical`: see [infra/ansible/README.md](infra/ansible/README.md). Place certs with strict perms; systemd units should `Restart=on-failure`.
- Terraform cloud templates live under [infra/terraform](infra/terraform); see its README for provisioning.

## Conventions & Constraints
- Prefer small, single-purpose functions; explicit error handling; validate inputs at boundaries.
- Do not add dependencies or invent files/APIs; follow existing module paths.
- Logging default off; only enable when `Mode.Debug` and not Ethics Mode.

## Examples
- Config validation lives in [code/config/config.py](code/config/config.py); entry flow in [code/main.py](code/main.py).
- Ingest HID usage via `managed_reset_button()` and `managed_avatar_button()` in [code/ingest/ingest.py](code/ingest/ingest.py).
- Audio/VAD parameters sourced from [code/ingest/internal.toml](code/ingest/internal.toml) and validated by [code/ingest/_config.py](code/ingest/_config.py).

Questions or ambiguities? Open a brief issue or ask to clarify config fields, TLS setup, or role boundaries. If parts of `hearing`/`vision`/`brain`/`output` need scaffolding, mirror ingest patterns and respect Ethics Mode constraints.

## Environment
  - If I invoke copilot locally, assume I am inside a devcontainer defined by .devcontainer/devcontainer.json. We will not be setting the devcontainer to privileged mode.
