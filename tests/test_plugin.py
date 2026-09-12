import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "omarchy-watch-codex"
    / "scripts"
    / "omarchy_watch_agent_hook.py"
)
HOOKS = (
    ROOT
    / "plugins"
    / "omarchy-watch-codex"
    / "hooks"
    / "hooks.json"
)


def load_adapter():
    spec = importlib.util.spec_from_file_location("watch_codex_adapter", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeSocket:
    def __init__(self):
        self.connected_to = None
        self.sent = b""
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, path):
        self.connected_to = path

    def sendall(self, content):
        self.sent += content

    def recv(self, _size):
        return b'{"ok":true}\n'


class AdapterTests(unittest.TestCase):
    def run_adapter(self, payload):
        adapter = load_adapter()
        client = FakeSocket()
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        with (
            mock.patch.object(adapter.socket, "socket", return_value=client),
            mock.patch.object(adapter, "socket_path", return_value=Path("/run/watch.sock")),
            mock.patch.object(adapter.time, "time", return_value=1234),
            mock.patch.object(sys, "stdin", stdin),
            mock.patch.object(sys, "stdout", stdout),
        ):
            adapter.main()
        return client, stdout.getvalue()

    def test_forwards_only_lifecycle_metadata(self):
        client, output = self.run_adapter(
            {
                "hook_event_name": "Stop",
                "session_id": "session-1",
                "turn_id": "turn-2",
                "prompt": "private prompt",
                "transcript_path": "/private/transcript.jsonl",
                "cwd": "/private/project",
                "model": "private-model",
                "permission_mode": "private-mode",
            }
        )

        self.assertEqual(output, "{}\n")
        self.assertEqual(client.connected_to, "/run/watch.sock")
        self.assertEqual(client.timeout, 0.1)
        self.assertEqual(
            json.loads(client.sent),
            {
                "command": "agent-event",
                "source": "codex",
                "session": "session-1",
                "turn": "turn-2",
                "event": "completed",
                "timestamp": 1234,
            },
        )

    def test_ignores_unknown_events(self):
        client, output = self.run_adapter(
            {"hook_event_name": "PreToolUse", "session_id": "session-1"}
        )

        self.assertEqual(output, "{}\n")
        self.assertIsNone(client.connected_to)
        self.assertEqual(client.sent, b"")

    def test_hook_manifest_uses_only_supported_events(self):
        document = json.loads(HOOKS.read_text())
        self.assertEqual(
            set(document["hooks"]),
            {"UserPromptSubmit", "Stop", "Interrupt", "SessionEnd"},
        )
        for groups in document["hooks"].values():
            self.assertEqual(len(groups), 1)
            handlers = groups[0]["hooks"]
            self.assertEqual(len(handlers), 1)
            self.assertIn("$PLUGIN_ROOT", handlers[0]["command"])


if __name__ == "__main__":
    unittest.main()
