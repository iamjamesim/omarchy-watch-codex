# Permission alert release checks

## Contract

The companion reports permission requests as needs-input without returning an
approval decision. It uses only lifecycle metadata, not command text or results.
It observes all local tool starts/ends to avoid clearing an outstanding request
when an unrelated tool finishes. A tool's ordinary start/completion produces no
extra watch event unless it opens or resolves a tracked input request.

The [Codex hook contract](https://learn.chatgpt.com/docs/hooks#permissionrequest)
has no permission-resolved event and no documented PermissionRequest call ID.
Consequently:

- Allow: attention clears when the approved tool finishes, not at the button click.
- Deny without a tool result: attention clears on Stop, Interrupt, SessionEnd,
  or the next UserPromptSubmit.
- Overlapping calls of the same tool: attention lasts until all candidate calls
  finish. This can overestimate waiting, but avoids clearing another request.
- Missing PreToolUse (for example, not trusted): the request still alerts, but
  remains until a lifecycle event clears it.
- Async questions and plain-text handoffs retain ordinary done alerts.

## Automated checks

```bash
OMARCHY_WATCH_REPO=/home/jamesim/Work/omarchy-watch python3 -m unittest discover -s tests
```

The socket integration uses a temporary runtime directory and the real bridge
handler. It does not contact the watch. Unit tests cover unrelated/overlapping
calls, a question alongside a permission request, duplicate requests, late
results from an old turn, privacy, and lifecycle cleanup.

## Physical acceptance in a fresh Codex session

Use the existing local marketplace, reinstall with a fresh development suffix,
and review the changed hooks in `/hooks`. All three tool hooks must be trusted.
Do not edit trust hashes. Existing sessions may retain their old plugin paths.

1. With ask-for-approval enabled, request a harmless elevated command (for
   example `true`, without sudo). While the prompt is open, check the bouncing
   robot and needs-input beep-beep. Allow it; check working/done afterward.
2. Repeat and deny. Check done after Codex concludes, with no stuck attention.
3. Repeat and interrupt the turn. Check attention clears.
4. In Plan mode, use `request_user_input`; answering must still resume working.
5. Run ordinary commands without approvals. They must not trigger needs-input.
6. Confirm two sessions preserve needs-input > done > working priority and
   tapping the watch acknowledges the alert without answering the prompt.

CLI 0.154.0 accepts the PermissionRequest hook configuration. Live prompt timing
and physical sound still require these acceptance checks after hook trust.
The companion needs the watch bridge/firmware with separate finished and
needs-input states (the local `ux/allowance-preview` watch branch).

## Rollback

The previous companion is on `ux/agent-input-state` at `b3c3353`. Reinstall that
revision with a fresh development suffix and start a new session. Reverting this
companion does not require flashing the watch or changing pairing.
