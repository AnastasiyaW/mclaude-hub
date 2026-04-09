"""
mclaude-hub - network and desktop layer for mclaude.

Extends the file-based mclaude library with:

- **hub**      - FastAPI + SQLite server that relays events between sessions on different machines
- **client**   - PyQt6 desktop app with tray icon, notifications, voice I/O
- **bridge**   - CLI adapter that connects a local Claude Code session to the hub
- **audio**    - STT and TTS backends (faster-whisper + pyttsx3 as defaults, pluggable)
- **common**   - shared data models and schemas used by all four above

The hub is additive. If the server is down, everything degrades to local file mode
(mclaude base library). If the desktop client is off, events queue in files and
surface later. Nothing hard-fails because a piece is missing.
"""

__version__ = "0.1.0"
