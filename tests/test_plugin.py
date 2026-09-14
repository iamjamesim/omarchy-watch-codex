import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
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
    def setUp(self):
        self.runtime = tempfile.TemporaryDirectory()
        self.addCleanup(self.runtime.cleanup)

    def run_adapter(self, payload):
        adapter = load_adapter()
        client = FakeSocket()
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        with (
            mock.patch.object(adapter.socket, "socket", return_value=client),
            mock.patch.object(adapter, "socket_path", return_value=Path(self.runtime.name) / "omarchy-watch.sock"),
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
        self.assertEqual(client.connected_to, str(Path(self.runtime.name) / "omarchy-watch.sock"))
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
            {"UserPromptSubmit", "Stop", "Interrupt", "SessionEnd",
             "PreToolUse", "PostToolUse", "PermissionRequest"},
        )
        for groups in document["hooks"].values():
            self.assertEqual(len(groups), 1)
            handlers = groups[0]["hooks"]
            self.assertEqual(len(handlers), 1)
            self.assertIn("$PLUGIN_ROOT", handlers[0]["command"])

        for event in ("PreToolUse", "PostToolUse"):
            self.assertNotIn("matcher", document["hooks"][event][0])

    def test_question_and_answer_lifecycle(self):
        for hook, expected in (("PreToolUse", "needs-input"),
                               ("PostToolUse", "working")):
            with self.subTest(hook=hook):
                client, output = self.run_adapter({
                    "hook_event_name": hook,
                    "session_id": "session-1", "turn_id": "turn-2",
                    "tool_name": "request_user_input", "tool_use_id": "question-1",
                    "tool_input": {"questions": "private question"},
                    "tool_response": {"answers": "private answer"},
                })
                command = json.loads(client.sent)
                self.assertEqual(command["event"], expected)
                self.assertEqual(command["turn"], "turn-2")
                self.assertEqual(set(command), {
                    "command", "source", "session", "turn", "event", "timestamp",
                })
                self.assertEqual(output, "{}\n")

    def test_unrelated_tools_and_async_questions_do_not_change_state(self):
        for tool in ("Bash", "apply_patch", "request_user_input_async"):
            for hook in ("PreToolUse", "PostToolUse"):
                with self.subTest(tool=tool, hook=hook):
                    client, output = self.run_adapter({
                        "hook_event_name": hook, "tool_name": tool,
                        "session_id": "session-1",
                    })
                    self.assertEqual(client.sent, b"")
                    self.assertEqual(output, "{}\n")

    def test_non_object_input_is_harmless(self):
        for payload in (None, [], "invalid"):
            client, output = self.run_adapter(payload)
            self.assertEqual(client.sent, b"")
            self.assertEqual(output, "{}\n")


class PermissionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.adapter = load_adapter()
        self.state = {}

    def event(self, hook, tool="Bash", call="command-1", turn="turn-1"):
        return self.adapter.transition(self.state, {
            "hook_event_name": hook, "tool_name": tool,
            "tool_use_id": call, "turn_id": turn,
        })

    def test_permission_and_tool_completion(self):
        for tool in ("Bash", "apply_patch", "mcp__example__tool"):
            with self.subTest(tool=tool):
                self.state.clear()
                self.assertIsNone(self.event("PreToolUse", tool))
                self.assertEqual(self.event("PermissionRequest", tool, None), "needs-input")
                self.assertEqual(self.event("PostToolUse", tool), "working")

    def test_unrelated_completion_does_not_clear_permission(self):
        self.event("PreToolUse")
        self.event("PreToolUse", "apply_patch", "edit")
        self.event("PermissionRequest", call=None)
        self.assertIsNone(self.event("PostToolUse", "apply_patch", "edit"))
        self.assertEqual(self.event("PostToolUse"), "working")

    def test_overlapping_same_tool_calls_clear_conservatively(self):
        self.event("PreToolUse", call="one")
        self.event("PreToolUse", call="two")
        self.assertEqual(self.event("PermissionRequest", call=None), "needs-input")
        self.assertIsNone(self.event("PostToolUse", call="one"))
        self.assertEqual(self.event("PostToolUse", call="two"), "working")

    def test_question_answer_does_not_clear_another_permission(self):
        self.event("PreToolUse")
        self.event("PermissionRequest", call=None)
        self.event("PreToolUse", "request_user_input", "question")
        self.assertIsNone(self.event("PostToolUse", "request_user_input", "question"))
        self.assertEqual(self.event("PostToolUse"), "working")

    def test_denial_without_tool_result_clears_at_stop_or_interrupt(self):
        for hook, expected in (("Stop", "completed"), ("Interrupt", "interrupted"),
                               ("SessionEnd", "ended"), ("UserPromptSubmit", "working")):
            with self.subTest(hook=hook):
                self.state.clear()
                self.event("PreToolUse")
                self.event("PermissionRequest", call=None)
                self.assertEqual(self.event(hook), expected)
                self.assertFalse(self.state.get("waiting"))

    def test_missing_pre_hook_still_alerts_and_never_guesses_resolution(self):
        self.assertEqual(self.event("PermissionRequest", call=None), "needs-input")
        self.assertIsNone(self.event("PostToolUse"))
        self.assertEqual(self.event("Stop"), "completed")

    def test_old_turn_results_cannot_clear_new_permission(self):
        self.event("UserPromptSubmit", turn="new")
        self.event("PreToolUse", turn="new")
        self.event("PermissionRequest", call=None, turn="new")
        self.assertIsNone(self.event("PostToolUse", turn="old"))
        self.assertIsNone(self.event("Stop", turn="old"))
        self.assertEqual(self.event("PostToolUse", turn="new"), "working")

    def test_repeated_request_does_not_repeat_alert(self):
        self.event("PreToolUse")
        self.assertEqual(self.event("PermissionRequest", call=None), "needs-input")
        self.assertIsNone(self.event("PermissionRequest", call=None))

    def test_permission_output_is_advisory_and_metadata_only(self):
        harness = AdapterTests()
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        client, output = harness.run_adapter({
            "hook_event_name": "PermissionRequest", "session_id": "session",
            "turn_id": "turn", "tool_name": "Bash",
            "tool_input": {"command": "private command"},
        })
        self.assertEqual(output, "{}\n")
        self.assertEqual(json.loads(client.sent)["event"], "needs-input")
        files = list(Path(harness.runtime.name).rglob("*.json"))
        self.assertEqual(len(files), 1)
        self.assertNotIn("private", files[0].read_text())
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
