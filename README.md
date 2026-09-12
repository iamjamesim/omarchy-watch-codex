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

The hook is optional. Codex will skip it until you review and trust its exact
definition. Removing or disabling this plugin turns off the integration without
affecting the watch's time, weather, theme synchronization, or pairing.

## Requirements

- Omarchy Watch and its desktop bridge must already be installed and running.
- Codex must support plugins and lifecycle hooks.

## Install

This repository is not public yet. Once published, installation will be:

```bash
codex plugin marketplace add iamjamesim/omarchy-watch-codex
```

Then open Codex, use `/plugins` to install **Omarchy Watch**, and use `/hooks`
to inspect and trust the four lifecycle hooks.

If an agent is helping with setup, it must explain the behavior above and ask
for explicit human approval before adding the marketplace or installing the
plugin. Mentioning the feature or installing the main Omarchy Watch plugin is
not consent to install this integration.

## Remove

Disable or remove **Omarchy Watch** from `/plugins`. This plugin does not write
to `~/.codex/hooks.json`, so no manual configuration cleanup is required.

## License

MIT. See [LICENSE](LICENSE).
