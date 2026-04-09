# Changelog

All notable changes to mclaude-hub will be documented in this file. Newest first.

## 0.1.0 - 2026-04-09

Initial alpha release. Four-component architecture:

### Added: common (shared models)

- `Event` dataclass with 15 EventType variants (session lifecycle, locks, messages, notifications, voice, handoff)
- `IdentityInfo`, `SessionInfo`, `LockClaim`, `MessagePayload` - schema mirroring the parent mclaude library
- Bidirectional conversion helpers (`to_dict`, `from_dict`) with enum-safe serialization

### Added: hub (FastAPI server)

- REST API: `/api/projects`, `/api/identities`, `/api/sessions`, `/api/locks`, `/api/events`
- WebSocket endpoint at `/ws` with per-project broadcast fan-out
- Bearer token authentication via `HubConfig.tokens` mapping
- Anonymous mode for dev and tests (`allow_anonymous=True`)
- SQLite storage with WAL journal mode, in-memory mode for tests
- Atomic lock claim semantics mirroring mclaude.locks
- Session lifecycle: start, heartbeat, end
- Event insertion with WebSocket broadcast on every write

### Added: bridge (Claude-to-hub adapter)

- `BridgeClient` with offline-first fallback to local file layer
- `send_message` - POSTs to hub, falls back to `mclaude.messages.MessageStore.send`
- `inbox` - GET from hub, falls back to local file scan
- `notify` - user-facing notification events
- `claim_lock` / `release_lock` - hub-authoritative with graceful offline failure
- `strict_online=True` mode for tests that want hub failures to raise

### Added: audio (STT/TTS backends)

- `SttBackend` and `TtsBackend` abstract interfaces
- `TranscriptionResult` dataclass
- `audio_registry` - process-wide registry of backends by name
- `StubSttBackend` - deterministic fake transcription, always returns "(stub transcription)"
- `StubTtsBackend` - records spoken text on instance, returns minimal valid WAV bytes
- Real backends (faster-whisper, pyttsx3, Coqui, Azure, ElevenLabs, Piper) are documented but not shipped in v0.1

### Added: client (PyQt6 desktop app)

- Lazy PyQt6 imports - module loads on headless machines without error
- Tray icon with identity/hub status
- Native notifications via plyer with Qt fallback
- Test TTS menu action that exercises the audio backend
- Skeleton only - real audio capture, hotkey handling, WebSocket client in v0.2

### Added: tests (40 total, all passing)

- `tests/hub/test_store.py` (9) - project, identity, session, lock, event CRUD + atomic claim
- `tests/hub/test_server.py` (9) - FastAPI TestClient integration including WebSocket roundtrip
- `tests/bridge/test_bridge.py` (6) - offline fallback, online mode with stubbed hub, broadcast, lock claim
- `tests/audio/test_audio.py` (7) - registry, stub backends, WAV header validity, unknown backend error
- `tests/test_common_models.py` (9) - dataclass defaults, enum serialization, from_dict roundtrip

### Design lessons learned the hard way

- `from __future__ import annotations` + FastAPI Depends = all authenticated endpoints return 422. Documented in `hub/server.py` top-of-file comment. Fix: do not use `__future__.annotations` in files with FastAPI routes.
- SQL placeholders must match bindings exactly (12 `?` + 13 values in tuple = ProgrammingError). Fix: count twice, cut once.

### Not yet implemented (coming in 0.2+)

- Real faster-whisper STT backend with sounddevice recording
- Real pyttsx3 TTS backend with cross-platform voice selection
- Desktop client hotkey handler (pynput)
- WebSocket client in desktop client (auto-reconnect, reconnect-on-wake)
- `mclaude-hub` CLI entry point for server startup
- `hub.toml` config loader
- TLS (expect users to put behind a reverse proxy)
- Mobile companion
