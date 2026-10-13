Recording, editing and mixing audio; an open-source, clean-room reimplementation of *Avid Pro Tools*, rebuilt in pure Rust: a complete digital audio workstation that runs natively and in the browser. Multitrack editing, a full mixer with plugins, sends and automation, MIDI, recording and bouncing, and every action scriptable from the command line or by an AI agent. 

**SoundCraft** follows the workflow audio engineers already know: an Edit window for arranging and editing, a Mix window for balancing, edit modes, tools, playlists, memory locations, *AudioSuite* processing and the rest. If you've spent years in that workflow, your hands should already know where things are.

- **Mix window**: Ten inserts and ten sends per track, busses and aux inputs, master faders, VCAs, routing folders, solo-in-place with implicit solo, and meters with peak hold.
- **MIDI editor**: Instrument tracks with built-in synths, a piano roll with a velocity lane, step input, quantize, transpose, and Standard MIDI File import and export.
- **Automation and markers**: breakpoint automation for volume, pan, mute, sends and every plugin parameter, written live in Write, Touch and Latch, plus memory locations and a big counter.
- **Surround and immersive**: main and bus formats from stereo to 9.1.6 and Ambisonics, a surround panner with divergence and height, object/bed routing and a Renderer window with live speaker levels.
- **Notation**: a Score Editor for MIDI tracks, MusicXML export for Sibelius and other notation programs, and printable engraved scores.
- **Your plugins too**: CLAP, VST3 and Audio Units, with their own editors, their state saved in the session, and every instance created off the audio thread.
- **Video**: A picture track with thumbnails and a Video window that follows the playhead, decoding H.264, ProRes and Motion JPEG in pure Rust, with timecode burn-in and sync offset.
