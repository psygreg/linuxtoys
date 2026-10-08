A fast, open-source, clean-room take on the *Adobe InDesign* workflow. 

- **Familiar**: *InDesign*'s layout, tools, menus, panels and shortcuts: spreads and parent pages, frames and threaded stories, the Control panel, paragraph and character styles, swatches, text wrap and more. If you know InDesign, you already know how to use it.
- **Beautiful type**: a Knuth–Plass paragraph composer (plus single-line), dictionary hyphenation (the public-domain Moby word list plus our own trained patterns), word, letter and glyph-scaling justification, keeps, optical margin alignment, columns, baseline grid, tabs, rules and shading. Line breaks are identical on screen and in PDF.
- **Fast**: multithreaded SIMD rendering (vello_cpu), copy-on-write documents with O(1) undo snapshots, and cached composition.
- **Open**: a documented native format, IDML import and export, PNG export, and PDF on the roadmap. No subscription, no licence server, no telemetry.
- **Agent-native**: every menu item, tool gesture, panel control and dialog can be driven over a JSON control channel and an MCP server, so Claude and other agents can lay out and edit documents like a designer.
- **Everywhere**: one Rust codebase for desktop and the web.
