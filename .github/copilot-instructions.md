# GitHub Copilot Instructions

## Core Principles

- Follow existing code style and patterns in this repository.
- Prefer clear, explicit, readable code over clever solutions.
- Keep functions small and single-purpose.
- Do not refactor or reformat unrelated code.

- Handle errors explicitly; do not silently ignore failures.
- Validate external input at boundaries.
- Avoid global state and hidden side effects.

- Do not introduce new dependencies unless explicitly requested.
- Do not invent APIs, files, or configuration that do not exist.

- If requirements are unclear, ask for clarification instead of guessing.
- Make minimal, incremental changes that are easy to review.
- Write meaningful comments and documentation for complex logic.
- **When reviewing, always consider the ethics statements made in [Ethics.md](../Ethics.md).**

## Project Architecture

This is an **AI Improv Toolkit**: a system for live improvisational theater with strict ethical constraints.

**Five core service roles** (defined in config's `Mode.Role`):
1. **ingest** – Captures button presses (HID) and audio (16kHz mono S16_LE) from USB mic; streams to hearing service via TLS-TCP framed protocol; publishes button events to NATS.
2. **hearing** – Processes audio via faster-whisper (not yet implemented).
3. **vision** – Processes video input (not yet implemented).
4. **brain** – Core orchestration and decision logic; subscribes to hearing/vision outputs; publishes to output.
5. **output** – Executes actions (text display, audio playback, etc.).
6. **health_check** – Monitors system health; publishes heartbeats to `health.<service>`.

**Communication patterns**:
- NATS pub/sub for inter-service events (mTLS required by default; plaintext dev mode explicit only).
- Custom TLS-TCP framed protocol for audio streaming (4B JSON length + JSON metadata + 4B audio length + raw PCM).
- Subject naming: `INTERFACE` (button events), `health.<service>` (heartbeats).

**Key files**:
- [code/config/config.py](../code/config/config.py) – Centralized config loader using Pydantic + TOML; all services consume this.
- [code/main.py](../code/main.py) – Entry point; role dispatcher via match statement.
- [code/testing/good_config.toml](../code/testing/good_config.toml) – Example config with `[Audio]`, `[Button]`, `[NATS]`, `[TLS]` sections.
- [code/ingest/IMPLEMENTATION_STAGES.md](../secrets/code_ingest_IMPLEMENTATION_STAGES.md) – Detailed stage-by-stage guide for ingest service (Stage -1 through Stage 10).

## Configuration & Validation

- Config is loaded once at startup via `config.generate_config(path)`.
- All settings are immutable after loading (TypedDict + Pydantic validation).
- Audio settings **must** be 16kHz mono S16_LE (webrtcvad and faster-whisper requirement).
- Ethics Mode (`Mode["Ethic"]=True`) **disables all logging and persistence**, enforces copyright-respecting AI tools, and overrides debug mode.
- Secrets (certs, keys, passwords) go in `secrets/` folder with `.no-git.*` or `.passwd` suffix; detect-secrets pre-commit enforces this.

## Development Workflow

- **Python environment**: Python 3.14+; use `uv` for dependency management (see `code/pyproject.toml`).
- **Type checking**: Mypy (strict mode) + Pydantic for validation; all code should be type-annotated.
- **Linting**: Ruff for style; pre-commit enforces on commit.
- **Testing**: Unit tests in `code/testing/` for config validation; end-to-end tests use OpenSSL, NATS CLI, and socat.
- **Logging**: Disabled by default; enabled only if `Mode["Debug"]=True` AND Ethics Mode is off. Use `logging.getLogger(__name__)`.

## Deployment & Infrastructure

- Dev container (`.devcontainer/Dockerfile`) installs system deps (portaudio19-dev, libasound2-dev, openssl, build-essential) and Python packages.
- Infrastructure as code: Terraform for cloud provisioning + Ansible for server config.
- Ansible roles: `base` (all servers), `physical` (physical hardware), `nats` (NATS broker), `ingest` (ingest service).
- PKI management: Run `infra/scripts/pki_manager.sh` to generate mTLS certs/keys; place in `secrets/pki/`; Ansible deploys to `/etc/show/pki` with perms `600` for keys.
- Systemd units run services with config paths; `Restart=on-failure` recommended.

## Pre-commit & Code Standards

- LF line endings enforced via `.gitattributes`.
- Pre-commit hooks: `ruff`, `mypy`, `markdownlint-cli2`, `terraform fmt`, `shellcheck`, `detect-secrets`, `ansible-lint`.
- Run `pre-commit install` once; hooks run on commit automatically.
- Update hooks: `pre-commit autoupdate`.
