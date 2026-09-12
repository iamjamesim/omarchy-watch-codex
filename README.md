# Omarchy Watch for Codex

Optional Codex activity indicators and completion alerts for
[Omarchy Watch](https://github.com/iamjamesim/omarchy-watch).

This integration is separate from the Omarchy Watch desktop plugin. Installing
Omarchy Watch does not install, enable, or modify Codex hooks.

## What opting in does

When you install this Codex plugin and trust its hooks, Codex runs the bundled
local adapter for `UserPromptSubmit`, `Stop`, `Interrupt`, and `SessionEnd`.
The adapter sends working, completed, interrupted, and ended state to the
Omarchy Watch bridge over its local Unix socket.

Codex supplies its standard hook payload to the adapter. The adapter accesses
only the hook event name and opaque session and turn IDs. It does not inspect,
store, or forward prompts, responses, transcripts, the working directory, the
model name, or permission settings. It makes no network requests.

The hooks are optional. Codex will skip them until you review and trust their
exact definitions. Removing or disabling this plugin turns off the integration
without affecting the watch's time, weather, theme synchronization, or pairing.

## Requirements

- Omarchy Watch and its desktop bridge must already be installed and running.
- Codex CLI with plugin and lifecycle-hook support.

## Install

Add the marketplace and install the plugin from your shell:

```bash
codex plugin marketplace add iamjamesim/omarchy-watch-codex
codex plugin add omarchy-watch-codex@omarchy-watch-codex
```

Start a new Codex CLI session, run `/hooks`, and inspect and trust the four
lifecycle hooks. No hook runs before you approve its current definition.

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
