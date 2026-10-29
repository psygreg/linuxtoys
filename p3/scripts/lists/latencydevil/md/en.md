**LatencyDevil** is a GPU-aware launcher wrapper for competitive gaming. It wraps a game's launch command, injects GPU-aware environment variables (discrete GPUs preferred) and then `exec`s the game, so the wrapper never lingers in the process tree — Steam keeps tracking the game as its direct child.

**How it works**

- Every wrapped launch gets `PROTON_USE_WAYLAND=1`, `LOW_LATENCY_LAYER=1` and `SDL_VIDEO_DRIVER=wayland`.
- With an NVIDIA GPU present, it additionally enables `LOW_LATENCY_LAYER_REFLEX=1` and sets `DXVK_CONFIG` to hide the AMD GPU from DXVK (`dxgi.hideAmdGpu = True`). An existing `DXVK_CONFIG` is preserved: the NVIDIA directive is appended newline-separated.
- **Flatpak handling**: when the wrapped command starts with `flatpak run`, variables are forwarded as `--env=KEY=VALUE` arguments, because Flatpak sandboxes drop environment variables they don't allow-list.
- GPU detection walks the PCI display-class devices in `/sys/bus/pci/devices`. If no GPU can be detected (unusual VM setups), the universal variable set is applied as a fallback.

**Usage**

- Steam launch options: `latencydevil -- %command%`
- Terminal, works with any command (Flatpak included): `latencydevil -- flatpak run app.id` or `latencydevil -- wine /path/to/game.exe`
- Debugging: `latencydevil --print` shows the variables that would be set, then exits; `latencydevil --debug -- <command>` also prints GPU detection, applied variables and the exec line.
