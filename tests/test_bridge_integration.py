"""Optional local adapter -> Unix socket -> watch bridge integration test."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from test_plugin import SCRIPT


@unittest.skipUnless(os.environ.get("OMARCHY_WATCH_REPO"),
                     "Set OMARCHY_WATCH_REPO to test against a local watch checkout")
class BridgeIntegrationTests(unittest.TestCase):
    def test_question_answer_completion_and_interrupt(self):
        path = (Path(os.environ["OMARCHY_WATCH_REPO"]) /
                "desktop/daemon/omarchy_watchd.py")
        spec = importlib.util.spec_from_file_location("watch_bridge", path)
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)

        with tempfile.TemporaryDirectory(prefix="watch-hooks-") as directory:
            watch = bridge.WatchDaemon.__new__(bridge.WatchDaemon)
            watch.agent_activity = bridge.AgentActivityLedger(Path(directory) / "state.json")
            watch.pending_agent_completions = {}
            watch.agent_activity_changed = mock.Mock()
            watch.log = mock.Mock()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(Path(directory) / "omarchy-watch.sock"))
                server.listen()
                server.settimeout(5)
                for hook, tool, call, expected in (
                    ("UserPromptSubmit", "Bash", "cmd", bridge.ACTIVITY_WORKING),
                    ("PreToolUse", "request_user_input", "question", bridge.ACTIVITY_ATTENTION),
                    ("PostToolUse", "request_user_input", "question", bridge.ACTIVITY_WORKING),
                    ("PreToolUse", "Bash", "cmd", None),
                    ("PermissionRequest", "Bash", None, bridge.ACTIVITY_ATTENTION),
                    ("PostToolUse", "Bash", "cmd", bridge.ACTIVITY_WORKING),
                    ("PreToolUse", "Bash", "denied", None),
                    ("PermissionRequest", "Bash", None, bridge.ACTIVITY_ATTENTION),
                    ("Stop", "Bash", None, bridge.ACTIVITY_FINISHED),
                    ("UserPromptSubmit", "Bash", "cancelled", bridge.ACTIVITY_WORKING),
                    ("PermissionRequest", "Bash", None, bridge.ACTIVITY_ATTENTION),
                    ("Interrupt", "Bash", None, bridge.ACTIVITY_NONE),
                ):
                    received = []
                    def receive():
                        with server.accept()[0] as connection:
                            connection.settimeout(5)
                            with connection.makefile("rb") as stream:
                                received.append(json.loads(stream.readline()))
                            connection.sendall(b'{"ok":true}\n')

                    listener = threading.Thread(target=receive, daemon=True)
                    if expected is not None:
                        listener.start()
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT)],
                        input=json.dumps({
                            "hook_event_name": hook,
                            "tool_name": tool, "tool_use_id": call,
                            "session_id": "local-test", "turn_id": "turn-1",
                        }), text=True, capture_output=True, timeout=5,
                        env={**os.environ, "XDG_RUNTIME_DIR": directory},
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "{}\n")
                    if expected is None:
                        continue
                    listener.join(timeout=5)
                    self.assertFalse(listener.is_alive())
                    self.assertEqual(len(received), 1)
                    # Exercise the real event handler; invoke its completion
                    # debounce callback explicitly instead of waiting 1.5s.
                    with mock.patch.object(bridge.GLib, "timeout_add", return_value=1):
                        watch.handle_agent_event(received[0])
                    if hook == "Stop":
                        watch.finish_agent_completion("codex", "local-test", "turn-1",
                                                      received[0]["timestamp"])
                    self.assertEqual(watch.agent_activity.aggregate()[0], expected, hook)


if __name__ == "__main__":
    unittest.main()
