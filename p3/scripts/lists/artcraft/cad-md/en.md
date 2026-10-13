Computer-aided design and drafting; an open-source, clean-room reimplementation of *Autodesk AutoCAD*, rebuilt in pure Rust: the command line, object snaps, layers, dimensions, hatches, blocks and DXF drawings you already know.

- **The workflow you know**: type `L`, click two points, type `@5<45`, press Enter. The command line, prompts with clickable `[Keywords]`, AutoComplete, object snaps, polar tracking, ortho, direct distance entry, window and crossing selection, grips, and right-click-to-repeat behave the way decades of drafting habit expect.
- **Open files**: DXF is read and written natively (ASCII and binary, R12 through 2018), and DWG files (R13 through 2018) open and save through the open-source acadrust library. Export to SVG and PNG today.
- **Fast and native**: Pure Rust and egui, no Electron, no web view.
- **Built for agents**: Every menu item, tool and prompt is a command. Agents can type at the command line exactly like a person, call any command with JSON, inspect the drawing to verify their work, and render it — over MCP, a JSON control channel, or the CLI.
- **Free**: MIT OR Apache-2.0, with no account and no subscription.
