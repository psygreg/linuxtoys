A fast, open-source, clean-room take on the *Adobe Illustrator* workflow.

- **Familiar**: *Illustrator*'s layout, tools, menus, panels and shortcuts: the Pen, Direct Selection, Pathfinder, Smart Guides, Appearance, Swatches, Layers and more. You already know how to use it.
- **Fast**: multithreaded SIMD rendering off the UI thread. 20,000 shapes render in about 27 ms at full retina resolution while the interface stays at 120 fps.
- **Robust**: exact curve booleans (no "cannot perform operation"), unlimited undo via structural sharing, and property-tested file round trips.
- **Open**: a documented native format (.vectorcraft, JSON), first-class SVG, PDF (and PDF-compatible .ai) import and export, PNG/JPEG/WebP export, Export for Screens, and SVGZ, templates, GIF, TIFF and BMP on open.
- **Agent-native**: every menu item, tool gesture, panel and dialog can be driven over a JSON control channel and an MCP server, so Claude and other agents can draw, edit and export the way a person does.
- **Everywhere**: One codebase for the desktop apps and the same UI in the browser.
