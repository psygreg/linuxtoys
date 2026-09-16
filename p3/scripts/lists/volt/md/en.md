Control panel for Vulkan games on Linux. Settings are applied by volt, an implicit Vulkan layer written in Rust, so they work on every driver.

21 settings across 5 tabs. Every one defaults to `default`, which leaves the game's own choice alone. A profile with everything on default does nothing.

| Tab | Section | Count | Covers |
|-----|---------|------:|--------|
| GPU | `[gpu]` | 1 | which device the game sees |
| Display | `[display]` | 4 | present mode, image count, compositing, clipping |
| Textures | `[textures]` | 7 | filtering, mips, anisotropy, LOD |
| Rendering | `[rendering]` | 4 | sample shading, alpha to coverage, alpha to one, depth clamp |
| Framerate | `[framerate]` | 5 | limit, offset, cadence, method, pacing |

Most option lists are read from your hardware, not from a table in volt-gui. Present modes, image counts, alpha modes, GPU names, anisotropy, mip levels and LOD bias all come from a probe of your own device. A setting your hardware lacks holds only `default`.

Fixed lists exist where there is nothing to read. `nearest` and `linear` are core Vulkan with no query behind them. The Framerate settings have nothing to read either, since a game never tells Vulkan what frame rate it wants.

Settings are read once at game start. Press Apply, then restart the game.

Use with:
```
volt -- ./game
```

or on Steam launch options:
```
volt -- %command%
```
