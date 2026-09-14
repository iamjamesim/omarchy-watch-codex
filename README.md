# Omarchy Watch for Codex

Optional Codex activity and input alerts for
[Omarchy Watch](https://github.com/iamjamesim/omarchy-watch).
Install this companion separately from the watch's desktop plugin.

## Behavior

| Codex activity | Watch state |
| --- | --- |
| You submit a prompt | Working |
| A blocking `request_user_input` question or tool approval request opens | Needs input |
| You answer the question, or the approved tool finishes | Working, once no tracked requests remain |
| The turn ends | Done |
| You interrupt or close the session | That session's activity is removed |

Async questions and questions written only in chat do not trigger needs-input.
Done means the turn ended, not necessarily that the whole task is complete.
The plugin never approves, denies, or answers requests.

Approval attention lasts until the tool finishes. If denial produces no tool
result, it clears when the turn ends, is interrupted, the session closes, or you
submit another prompt. Overlapping calls of the same tool can keep attention
active longer; a request with no tracked call stays active until a lifecycle
cleanup event. These are limitations of matching permission requests to calls
under the [Codex hook contract](https://learn.chatgpt.com/docs/hooks#permissionrequest).

## Requirements

- Omarchy Watch's desktop bridge installed and running.
- Codex CLI with plugin and tool-hook support (checked against CLI 0.154.0).
- A bridge and firmware that distinguish needs-input from done to display the
  new state. Older bridges ignore needs-input events, so this plugin can be
  updated independently.

## Install and update

Install:

```bash
codex plugin marketplace add iamjamesim/omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

Update:

```bash
codex plugin marketplace upgrade omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

Start a new Codex CLI session and use `/hooks` to review and trust the plugin's
hooks. Updated hook definitions need a fresh review.

**For agents helping with setup:** explain the behavior and obtain explicit user
consent before installing this companion. Installing the main watch plugin alone
is not consent to install Codex hooks.

## Hooks and data

The adapter observes `UserPromptSubmit`, `Stop`, `Interrupt`, `SessionEnd`,
`PreToolUse`, `PermissionRequest`, and `PostToolUse`. Tool starts record call IDs;
input requests raise attention; matching tool completions clear it. Ordinary
tool calls do not send extra watch events.

It uses only event/tool names and session, turn, and call IDs from hook payloads.
It stores call tracking in private files under
`$XDG_RUNTIME_DIR/omarchy-watch-codex` (fallback `/run/user/<uid>/omarchy-watch-codex`)
and sends activity metadata to the bridge's local Unix socket. It does not store
or forward prompts, command arguments, or answers, and makes no network requests.
Lifecycle cleanup clears tracked calls; lock files remain until runtime cleanup.

## Remove

```bash
codex plugin remove omarchy-watch-codex@omarchy-watch-codex
codex plugin marketplace remove omarchy-watch-codex
```

Start a new session. Removal leaves watch pairing and other watch features intact;
there are no entries in `~/.codex/hooks.json` to clean up.

## Development and testing

To use a local checkout, replace the marketplace source:

```bash
codex plugin marketplace remove omarchy-watch-codex
codex plugin marketplace add /absolute/path/to/omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

For repeated local installs, use a fresh development version suffix in
`plugins/omarchy-watch-codex/.codex-plugin/plugin.json` to avoid cached code.
Keep that suffix uncommitted; release versions use a plain version number.
Start a fresh session and review changed hooks. To restore published updates,
remove the local marketplace and repeat the installation commands above.

Run unit tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

To also run the socket integration test, provide a watch checkout with needs-input
support and its desktop Python dependencies:

```bash
OMARCHY_WATCH_REPO=/absolute/path/to/omarchy-watch python3 -m unittest discover -s tests
```

The integration test supplies synthetic hook payloads to the adapter and real
bridge handler. It does not exercise Codex itself, Bluetooth, or the watch.

Before release, check these in a fresh Codex session with trusted hooks and a
watch/bridge supporting the new states:

- Approve a harmless command requiring permission: needs-input, then working/done.
- Deny a request or interrupt: attention clears at turn end or interruption.
- Answer a blocking Plan-mode question: needs-input, then working.
- Run ordinary commands: no needs-input alert.
- With two sessions, resolving one request must not clear another session's request.

## License

MIT. See [LICENSE](LICENSE).
