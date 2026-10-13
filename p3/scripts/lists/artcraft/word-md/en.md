Writing and document design; an open-source, clean-room reimplementation of *Microsoft Word*, rebuilt in pure Rust: a fast word processor with the *Word* workflow you already know: the ribbon, styles, tables, track changes, references and mail merge.

- **Familiar**: *Word*'s ribbon tabs, groups, shortcuts and behaviour: Enter continues a list, Tab demotes it, Ctrl/⌘+B bolds the word under the caret, the Styles gallery previews styles live, F4 repeats, F7 checks spelling, F8 extends the selection.
- **Your files**: opens and saves .docx (OOXML), and also .odt, .rtf, .html, .md, .tex (LaTeX), .txt; opens *Word* 97-2003 .doc; exports PDF with real, selectable text, links and bookmarks.
- **Fast**: paragraph layout is cached, so typing in a 188-page document re-lays it out in about 1.4 ms; pages render on demand.
- **Built for agents**: every action is a command with an id. The same 422 commands drive the ribbon, keyboard shortcuts, the command search, a command-line tool, a JSON control channel and an MCP server.
- **Private**: spelling, grammar and everything else work offline.
- **Open**: MIT OR Apache-2.0. Clean-room: built from public specifications and observation, with every asset original or openly licensed.
