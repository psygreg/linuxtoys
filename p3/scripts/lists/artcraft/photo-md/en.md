Layers, masks, adjustment layers, layer styles, type, vectors, brushes and real PSD files, in a native app written entirely in Rust. Open source, offline, and yours. 

- **Familiar by design**: the menus, shortcuts, panels and tools are where your hands expect them, from ⌘J to ⇧⌘D. If you know Photoshop, you already know PhotoCraft.
- **Native and fast**: a GPU compositor on wgpu (Metal, Vulkan, DX12, WebGPU), copy-on-write tiles and multithreaded filters. No Electron, no web view, no waiting. 	
- **Real PSD files**: open, edit and save layered Photoshop documents. Re-saving keeps the render of 307 of the 309 psd-tools test files. 
- **Agent-ready**: every action is a command, so you can drive the same engine from the UI, the CLI, a JSON control channel or an MCP server.
