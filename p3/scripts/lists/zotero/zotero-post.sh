#!/usr/bin/env bash

chmod +x "$LINUXTOYS_TARBALL_DIR/set_launcher_icon"
."$LINUXTOYS_TARBALL_DIR/set_launcher_icon"
ln -s "$LINUXTOYS_TARBALL_DIR/zotero.desktop" ~/.local/share/applications/zotero.desktop