**Prism** is a beginner-friendly live media trigger and overlay tool built with Qt 6, FFmpeg, and OpenGL. Perfect for school events, small concerts, and sports—combining the simplicity of instant clip triggering with the power of live visual control. 

- **Node Graph Canvas**: free-form visual pipeline — wire Input → Process → Layer → A/B Select → Output nodes; zoom, pan, and minimap for large shows
Process & Layer Nodes: Crop, flip, and ML background removal in Process nodes; stack and layout multiple inputs in Layer nodes with canvas sizing and transform editing
- **AI Background Removal**: Remove-Background process node runs MediaPipe's selfie-segmentation model (via ONNX Runtime) to key out a webcam's background live, compositing the subject over the layers below
- Multiple Media Source Types: video files, images, slideshows, webcams, screen/window capture, custom canvases, GLSL shaders, SVG templates, text, NDI inputs, and phone cameras (WebRTC)
- **Live A/B Deck Mixing**: crossfade between two decks with per-deck speed, AUTO / CUT, and many transition modes (wipes, slides, dips, 3D cube/flip, and more)
- **Master Audio Routing**: master audio-input and master audio-output nodes for per-device capture and mixing inside the graph
- **Source Editing*: Per-input trim, crop, transform, and composited text/image overlays via dedicated edit dialogs
- SVG Templates: data-driven scoreboards, clocks, countdown timers, lower thirds, and bugs from SVG files with {token} placeholders, rendered with Skia
- Lua Scripting: script nodes that generate live text/data overlays via an embedded Lua runtime (sol2, optional at build time)
- **Phone Camera (WebRTC)**: Stream a smartphone camera into CutWire Prism over LAN or a public relay, paired by QR code
- Panic Controls: emergency Blackout, Pause (freeze on current frame), and Stay Tuned overlay
- Program Output Hub: mirror windows, optional NDI program output, virtual-camera output, program video recording with markers, FLAC program-audio recording, and freeze-frame capture
- **OBS Integration**: optional WebSocket connection for scene switching and per-source OBS scene links
- Remote Control: built-in server for triggering sources and decks from another device on the network
- Agent Access: Optional localhost MCP server so Cursor, Claude Code, or other agents can drive the mixer
- Real-time Playback: FFmpeg decoding on a background thread with low-latency OpenGL compositing and hardware acceleration
