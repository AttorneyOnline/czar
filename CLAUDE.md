# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Czar is the official Python server for Attorney Online (courtroom roleplay game). Forked from tsuserver3. Built on asyncio with a custom text-based network protocol.

## Commands

```bash
# Install dependencies
uv sync

# Run server
uv run python start_server.py

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Run tests (via tox, targets py312)
uv run tox

# Run tests directly
uv run pytest -q

# Run a single test file
uv run pytest tests/test_ms_parser.py -q

# Run a single test
uv run pytest tests/test_ms_parser.py::test_parse_pre26 -q
```

## Architecture

**Hierarchy:** `CzarServer` → `HubManager` → `Hub (AreaManager)` → `Area` → `Client`

- **Hubs** are lobbies. **Areas** are rooms within a hub. **Clients** are connected players.
- `server/czar.py` — Main server class. Loads config, manages music/characters/backgrounds.
- `server/client.py` — Per-connection state (character, position, muting, permissions).
- `server/area.py` — Room logic (players, timers, evidence, music, backgrounds).
- `server/client_manager.py` / `server/area_manager.py` / `server/hub_manager.py` — Collection managers.
- `server/database.py` — SQLite persistence for bans, logs, user info.
- `server/evidence.py` — Courtroom evidence system.

**Network layer** (`server/network/`):
- `aoprotocol.py` — Main AO protocol handler over TCP (port 27016). Commands are `#`-separated, packets end with `#%`.
- `aoprotocol_ws.py` — WebSocket variant (port 50001).
- `ms_parser.py` — Parses in-character messages across multiple client protocol versions (pre-2.6, 2.6, 2.8, AO Golden, KFO, DRO).
- `masterserverclient.py` — Registers with the master server list.

**Command system** (`server/commands/`):
- Commands are functions named `ooc_cmd_<name>` and must be listed in each module's `__all__`.
- `commands/__init__.py` routes commands via `call(client, cmd, arg)` using dynamic `getattr`.
- `mod_only()` decorator restricts commands to moderators/area owners/hub owners.
- The command system supports hot-reloading via `commands.reload()`.
- 12 command modules: admin, area_access, areas, battle, casing, character, fun, hubs, inventory, messaging, music, roleplay.

## Key Patterns

- **Exceptions for user errors:** `ClientError`, `AreaError`, `ArgumentError`, `ServerError` in `server/exceptions.py`. Commands raise these to send error messages to the client.
- **Config from YAML:** Server config lives in `config/` (copied from `config_sample/` on first run). Areas, music lists, and characters defined in YAML. Character emotes loaded from INI files.
- **Ruff config:** Line length 120, target Python 3.11, `E741` ignored globally, `E402`/`F403` ignored in `commands/__init__.py`.

## Testing

Tests are in `tests/` using pytest. Mock infrastructure in `tests/mock/mocks.py` provides `MockServer`, `MockClient`, and `MockClientManager` for testing the protocol handler without a full server.
