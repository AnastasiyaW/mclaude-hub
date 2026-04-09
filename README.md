# mclaude-hub

**The network, desktop, and audio layer for [mclaude](https://github.com/AnastasiyaW/mclaude).**

Where `mclaude` is a pure-Python file-based library for Claude Code session collaboration (locks, handoffs, memory, registry, messages), `mclaude-hub` adds the three things you need when your Claude sessions start living on more than one machine:

1. A **hub server** that relays events between sessions on different computers
2. A **desktop client** with a tray icon, native notifications, voice input, and text-to-speech so Claude can notify you while you are making coffee
3. A **Claude bridge** that connects a local Claude Code session to the hub and falls back to file-based mclaude when the network is down

Everything is optional. The hub is an accelerator, not a requirement - if the server is offline, the bridge writes to `.claude/messages/` and the mclaude library picks up the data locally. Nothing hard-fails because a piece is missing.

---

## One scene that explains why

> It's 10:34 AM. You ask your Claude to run the overnight training job. It starts, 4 hours of work ahead. You close your laptop and go for a walk.
>
> 12:17 PM. The job finishes. Your phone buzzes. You look: *"Claude ani - training done, accuracy 0.847 on the validation set, 3 tests failing"*. You tap the notification and speak into your phone: *"rerun the 3 failing tests with the bigger LR"*. The desktop client in your house transcribes it, sends it to your laptop over the hub, your Claude resumes, fixes the tests, and posts another notification 20 minutes later.
>
> Meanwhile your teammate Vasya on his own laptop sees in his tray: *"ani is reworking the training config, don't touch model_training/ until 14:00"*. No coordination call needed.

That is what this repo builds. Not magic, not a wrapper around a new Anthropic cloud product - just a small network layer plus a small desktop app plus a small adapter that connects to Claude Code.

---

## Architecture at a glance

```
┌──────────────────────────────┐          ┌──────────────────────────────┐
│  Your laptop                 │          │  Teammate's laptop           │
│                              │          │                              │
│  Claude Code session         │          │  Claude Code session         │
│          ↕                   │          │          ↕                   │
│  Claude Bridge ──────┐       │          │       ┌────── Claude Bridge  │
│          ↕           │       │          │       │           ↕          │
│  Desktop Client      │       │          │       │    Desktop Client    │
│  (tray, voice, TTS)  │       │          │       │   (tray, voice, TTS) │
│                      │       │          │       │                      │
└──────────────────────┼───────┘          └───────┼──────────────────────┘
                       │                          │
                       │    HTTPS + WebSocket     │
                       └──────────┬───────────────┘
                                  │
                      ┌───────────▼────────────┐
                      │   Hub Server           │
                      │   FastAPI + SQLite     │
                      │   + WebSocket broadcast│
                      │   + bearer token auth  │
                      └────────────────────────┘
```

All four components are separate Python modules in one package. You can run just the hub on a VPS. You can run just the desktop client on your laptop. You can run just the bridge as a subprocess next to Claude Code. They find each other via config files.

See [docs/architecture.md](docs/architecture.md) for the full walkthrough: data flows for every scenario, threading model, security model, testing strategy, and rationale for every dependency choice.

---

## What's in the package

```
mclaude_hub/
├── common/           shared data models (Event, IdentityInfo, SessionInfo, LockClaim, MessagePayload)
├── hub/              FastAPI server + SQLite store + WebSocket broadcaster
├── bridge/           HTTP client + file fallback - the Claude-to-hub adapter
├── audio/            STT and TTS backend interfaces + stub implementations
└── client/           PyQt6 desktop app skeleton (tray, notifications, lazy imports)
```

Each subpackage has its own README and tests. Run `pytest tests/` to run all 40 of them.

---

## Installation

### Hub server (run once, somewhere reachable)

```bash
pip install mclaude-hub
uvicorn mclaude_hub.hub.server:create_app --factory --host 0.0.0.0 --port 8080
```

Or put it behind a reverse proxy with TLS (Caddy, nginx, Cloudflare Tunnel) - the hub server itself does not terminate TLS.

### Desktop client (run on every machine)

```bash
pip install "mclaude-hub[client]"
python -m mclaude_hub.client
```

This requires PyQt6 and plyer. On Linux you also need system libraries for libnotify. On Windows and macOS it should work out of the box.

### Audio backends (optional)

```bash
# Local speech-to-text via faster-whisper
pip install "mclaude-hub[audio-stt]"

# Cross-platform text-to-speech via pyttsx3
pip install "mclaude-hub[audio-tts]"

# Both
pip install "mclaude-hub[audio-full]"
```

The audio modules ship stub backends out of the box. Real backends are loaded lazily when you configure them in the client settings - so you do not need a 1 GB Whisper model on disk unless you actually want voice input.

### Claude bridge (run next to Claude Code)

```bash
pip install mclaude-hub
# In your Claude Code hook or startup script:
from mclaude_hub.bridge import BridgeClient, BridgeConfig
bridge = BridgeClient(BridgeConfig(
    hub_url="https://your-hub.example.com",
    token="your-bearer-token",
    identity="ani",
    project_id="my-project",
))
```

---

## Quick test of the whole pipeline

```bash
# In one terminal, start the hub
uvicorn mclaude_hub.hub.server:create_app --factory --host 127.0.0.1 --port 8080

# In another terminal, run the test bridge
python -c "
from mclaude_hub.bridge import BridgeClient, BridgeConfig
bridge = BridgeClient(BridgeConfig(
    hub_url='http://127.0.0.1:8080',
    identity='test-user',
    project_id='default',
))
# The hub in anonymous mode (default for dev) accepts everything
bridge.send_message(to='*', type='broadcast', subject='Hello from the test bridge')
print('done')
"

# In a third terminal, start the desktop client
python -c "
from mclaude_hub.client import ClientConfig, run_client
run_client(ClientConfig(
    hub_url='http://127.0.0.1:8080',
    identity='test-user',
    project_id='default',
))
"
```

You should see a tray icon appear with a welcome notification. Right-click for the menu. The `Send test notification` action will pop a native desktop notification.

---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/
```

Current state: **40 tests, all passing.**

- `tests/hub/test_store.py` - SQLite store unit tests (9 tests)
- `tests/hub/test_server.py` - FastAPI integration via TestClient + WebSocket (9 tests)
- `tests/bridge/test_bridge.py` - BridgeClient online and offline modes (6 tests)
- `tests/audio/test_audio.py` - audio backend registry and stub backends (7 tests)
- `tests/test_common_models.py` - shared data model unit tests (9 tests)

The test suite does not need a microphone, speaker, display, or network. Everything is in-memory or stubbed. This is intentional - the audio pipeline works with pre-recorded WAV fixtures, the GUI is never instantiated in unit tests (it is a skeleton loaded lazily by `run_client()`), and the hub server uses FastAPI's `TestClient` with an in-memory SQLite.

Cross-platform CI runs the same suite on Ubuntu, Windows, and macOS against Python 3.10, 3.11, and 3.12.

---

## Design principles (non-negotiable)

These are the rules contributions must respect. They are the same rules as the parent `mclaude` library.

1. **File-based degradation.** The hub is an accelerator. When it is offline, the bridge writes to local `.claude/` files and nothing is lost. This is the most important property - without it, adding a network dependency to Claude Code would be strictly worse than pure files.

2. **Format compatibility with mclaude.** The hub's message schema is intentionally the same as `mclaude.messages.Message`. You can dump hub events to local files, scan local files and push to the hub, or run both side by side - no translation required.

3. **Zero required audio dependencies.** The stub backends let the rest of the package run on machines without faster-whisper, pyttsx3, sounddevice, numpy, or any of the heavy audio stuff. Real backends are optional installs.

4. **Lazy GUI imports.** `mclaude_hub.client` is importable on headless machines. PyQt6 only loads when you call `run_client()`. Tests run in CI without any display.

5. **Single instance, no HA.** The hub is designed to be run by one team on one VPS. Not a SaaS, not a clustered service. Good for up to dozens of concurrent users. If you outgrow it, switch to Postgres (schema is ready) and add a second instance behind a sticky-session load balancer.

6. **Bearer tokens, not OAuth.** Auth is a map of `token -> (project_id, identity)` in a config file. Revocation is editing the file. If you need stronger auth, put the hub behind Tailscale or a reverse proxy that does OIDC.

---

## Roadmap

- **v0.1** (this release) - Hub server, bridge, audio stubs, desktop client skeleton, full test suite
- **v0.2** - Real faster-whisper STT, real pyttsx3 TTS, hotkey recording, notification polish
- **v0.3** - Mobile companion (Flutter), wake word detection, E2E encryption opt-in
- **v0.4** - Team dashboards, activity feed, on-call rotation, optional Postgres backend

---

## What this is NOT

- **Not a Claude Code replacement.** We assist Claude Code, not replace it.
- **Not an Anthropic product.** This is a community library. Anthropic ships their own Claude Code on the Web and Remote Control features that overlap in some areas (see [docs/comparison-with-anthropic-cloud.md](docs/comparison-with-anthropic-cloud.md) for the full comparison). mclaude-hub is the open, self-hosted, file-compatible alternative.
- **Not a MemPalace fork.** The memory layer (in the parent `mclaude` repo) borrows ideas from [MemPalace](https://github.com/milla-jovovich/mempalace) research but ships zero dependencies on their code.
- **Not a new Claude Code UI.** The desktop client is a tray app with notifications and audio - it does not replace your terminal or IDE.

---

## License

MIT. See [LICENSE](LICENSE).

## Credits

- **mclaude** - the parent library that this extends
- **MemPalace** (Milla Jovovich, Ben Sigman) - for the hierarchical memory graph concept and the raw-verbatim research
- **Paperclip** - for the heartbeat pattern
- **DeerFlow 2.0** (ByteDance) - for making us think harder about the isolation-vs-coordination tradeoff
- **Claude Code** (Anthropic) - for being the harness this sits next to
- **faster-whisper**, **pyttsx3**, **PyQt6**, **FastAPI** - for being the tools that make the whole thing possible
