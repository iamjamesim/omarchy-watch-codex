#!/usr/bin/env python3
"""Forward supported Codex lifecycle state to omarchy-watchd, best effort."""

import json
import os
from pathlib import Path
import socket
import sys
import time


EVENTS = {
    "UserPromptSubmit": "working",
    "Stop": "completed",
    "Interrupt": "interrupted",
    "SessionEnd": "ended",
}


def socket_path() -> Path:
    root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return root / "omarchy-watch.sock"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            print("{}")
            return
        event = EVENTS.get(str(payload.get("hook_event_name", "")))
        # Match only the blocking question tool. Async questions return before
        # the answer arrives, so their PostToolUse is not a resume signal.
        if payload.get("tool_name") == "request_user_input":
            event = {
                "PreToolUse": "needs-input",
                "PostToolUse": "working",
            }.get(payload.get("hook_event_name"), event)
        session = str(payload.get("session_id", ""))
        if event and session:
            command = {
                "command": "agent-event",
                "source": "codex",
                "session": session,
                "turn": str(payload.get("turn_id", "")),
                "event": event,
                "timestamp": int(time.time()),
            }
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.1)
                client.connect(str(socket_path()))
                client.sendall((json.dumps(command) + "\n").encode())
                client.recv(4096)
    except (BrokenPipeError, ConnectionError, OSError, TypeError, ValueError,
            json.JSONDecodeError):
        # Watch availability must never affect a Codex turn.
        pass
    print("{}")


if __name__ == "__main__":
    main()
