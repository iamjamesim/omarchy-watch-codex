# Omarchy Watch for Codex

Optional Codex activity indicators and completion alerts for
[Omarchy Watch](https://github.com/iamjamesim/omarchy-watch).

This integration is separate from the Omarchy Watch desktop plugin. Installing
Omarchy Watch does not install, enable, or modify Codex hooks.

## What opting in does

When you install this Codex plugin and trust its hooks, Codex runs the bundled
local adapter for `UserPromptSubmit`, `Stop`, `Interrupt`, and `SessionEnd`,
plus `PreToolUse`, `PermissionRequest`, and `PostToolUse`.
The adapter sends working, needs-input, completed, interrupted, and ended state to the
Omarchy Watch bridge over its local Unix socket.

A blocking structured question or permission request marks the agent as needing
input. Returning from the question or finishing the approved tool restores working
once no tracked requests remain. Finishing the turn remains a separate completed
state. Asynchronous questions and questions written only in prose do not produce
needs-input; ordinary turn completion still produces the done alert. No hook
approves, denies, or answers anything for you.

Codex does not expose a permission-resolved hook. Attention therefore remains
while an approved command runs. A denied request without a tool-completion event
clears on turn completion, interruption, session end, or the next user prompt.
PermissionRequest does not document a call ID: overlapping calls of the same tool
are conservatively held until all candidate calls finish. If the corresponding
PreToolUse hook is unavailable, attention clears at the next lifecycle event.

Codex supplies its standard hook payload to the adapter. The adapter accesses
only the hook event name, tool name, and opaque session, turn, and tool-call IDs.
It keeps temporary call-tracking files under
`$XDG_RUNTIME_DIR/omarchy-watch-codex` (fallback `/run/user/<uid>`), with private
directory/file permissions. Lifecycle events clear the tracked calls; small lock
files remain until the runtime directory is cleared. It does not inspect, store,
or forward prompts, command arguments, responses, transcripts, the working
directory, the model name, or permission settings. It makes no network requests.

The hooks are optional. Codex will skip them until you review and trust their
exact definitions. Removing or disabling this plugin turns off the integration
without affecting the watch's time, weather, theme synchronization, or pairing.

## Requirements

- Omarchy Watch and its desktop bridge must already be installed and running.
- Codex CLI with plugin and lifecycle-hook support.
- Input detection requires tool hooks (implementation checked against Codex
  CLI 0.154.0; permission lifecycle follows the current documented hook contract)
  and the updated Omarchy Watch bridge/firmware with separate
  needs-input and finished states.

## Install

Add the marketplace and install the plugin from your shell:

```bash
codex plugin marketplace add iamjamesim/omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

Start a new Codex CLI session, run `/hooks`, and inspect and trust the
hooks. No hook runs before you approve its current definition.

If an agent is helping with setup, it must explain the behavior above and ask
for explicit human approval before adding the marketplace or installing the
plugin. Mentioning the feature or installing the main Omarchy Watch plugin is
not consent to install this integration.

## Update

Refresh the marketplace and reinstall the plugin, then start a new Codex CLI
session. If a hook definition changed, `/hooks` will require a fresh review.

```bash
codex plugin marketplace upgrade omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

## Local development

To test a checkout instead of the published marketplace, replace the registered
source (this changes where future plugin updates come from):

```bash
codex plugin marketplace remove omarchy-watch-codex
codex plugin marketplace add /absolute/path/to/omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

Use a fresh development version suffix in `plugin.json` when reinstalling edited
code so Codex does not reuse a cached copy. Start a new session and review the
changed hooks with `/hooks`. In Plan mode, ask Codex to use `request_user_input`:
the watch should bounce while the question is open, pulse after answering, then
sway when the turn finishes. This requires the updated bridge and watch firmware;
installing this companion alone does not update either of them.

For permission alerts, review all three tool hooks: PreToolUse records call IDs,
PermissionRequest raises attention, and PostToolUse resolves tracked calls. See
[the release checks](docs/permission-alerts.md) for approval, denial, cancellation,
and concurrent-call testing.

Run adapter tests from this repository:

```bash
python -m unittest discover -s tests
```

With the watch repository's desktop Python dependencies available, also test
the real adapter process through a temporary Unix socket into the bridge's event
handler. This test does not contact Bluetooth or change the running watch state:

```bash
OMARCHY_WATCH_REPO=/absolute/path/to/omarchy-watch python -m unittest discover -s tests
```

To restore published updates, remove the local marketplace and repeat the
marketplace/install commands in **Install**.

## Remove

Uninstall the plugin:

```bash
codex plugin remove omarchy-watch-codex@omarchy-watch-codex
```

To stop tracking its marketplace as well, run:

```bash
codex plugin marketplace remove omarchy-watch-codex
```

This plugin does not write to `~/.codex/hooks.json`, so no manual configuration
cleanup is required.

## License

MIT. See [LICENSE](LICENSE).
