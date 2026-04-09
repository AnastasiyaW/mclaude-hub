# AGENTS.md

This repository is **mclaude-hub**, the network/desktop/audio extension for the [mclaude](https://github.com/AnastasiyaW/mclaude) library. It provides four components that let multiple Claude Code sessions collaborate across machines: a hub server, a Claude bridge, an audio subsystem, and a desktop client.

## What to use this for

When the user asks you to work with or extend mclaude-hub:

- **Hub server changes** - code in `mclaude_hub/hub/`. Tests in `tests/hub/`. The server is FastAPI + SQLite + WebSockets. In-memory store for tests via `Store(":memory:")`.
- **Bridge client changes** - code in `mclaude_hub/bridge/`. Tests in `tests/bridge/`. The bridge is httpx + mclaude file fallback. Tests can override `bridge._http` with a `TestClient` to avoid real network.
- **Audio backend changes** - code in `mclaude_hub/audio/`. New backends register themselves in `audio_registry` at import time. The `stubs` module is the reference for minimal backend structure.
- **Desktop client changes** - code in `mclaude_hub/client/`. This is the only place that imports PyQt6, and it does so lazily inside `run_client()`. Never add a top-level `import PyQt6` - it would break headless CI.

## Rules specific to this repo

1. **Never add `from __future__ import annotations` to files that contain FastAPI routes.** The stringified annotations that PEP 563 produces break FastAPI's Depends resolver - `token: Annotated[TokenInfo, Depends(authorize)]` becomes a string, FastAPI cannot introspect it, and the parameter falls through to being a required query parameter. The result is every authenticated endpoint returning 422 "Field required". I learned this the hard way; the comment at the top of `hub/server.py` explains it.

2. **Never import PyQt6 at module top level.** Only inside functions that will be called from `run_client()` or the client module's internal entry points. This keeps the package importable on machines without Qt.

3. **Never introduce a hard dependency on faster-whisper, pyttsx3, or sounddevice.** They are optional extras. The stub backends must always work.

4. **The hub is additive.** Every operation that goes to the hub must have a file-based fallback via the parent `mclaude` library. If the hub is unreachable, the bridge should degrade gracefully and return a sensible result, not crash.

5. **All SQLite writes must go through `Store._tx()`** which takes the threading lock. Direct `self._conn.execute` without the lock will race on write.

6. **Format compatibility with mclaude.messages is mandatory.** The `Event` schema and the `MessagePayload` helper exist to make hub events and local message files interchangeable. Breaking that symmetry would force a translation layer on every consumer.

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/
```

All 40 tests should pass in under 3 seconds. If they do not, do not ship the change.

Cross-platform CI runs on Ubuntu, Windows, macOS with Python 3.10, 3.11, 3.12. Add tests before adding features.

## Do not touch

- `mclaude_hub/hub/server.py` - the annotation rule above. If you must add features, read the note at the top first.
- `mclaude_hub/audio/base.py` - the SttBackend and TtsBackend interfaces. Changing them breaks every backend.
- `mclaude_hub/common/models.py` - the schema. Changes must come with a migration plan if they break existing event payloads.

## Context engineering

This file is kept under 100 lines to fit in a single cached prompt prefix. The parent README.md has the detailed walkthrough; read that first if you need to understand the architecture. Do not duplicate that content here.
