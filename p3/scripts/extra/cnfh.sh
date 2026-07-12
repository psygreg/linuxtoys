#!/bin/bash
# name: Distrobox Command Handler
# version: 1.0
# description: dch_desc
# icon: cnfh.svg
# nocontainer: invert

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# Create the command-not-found handler
# --- End of script code ---
sudo_rq
sudo ln -s /usr/bin/distrobox-host-exec /usr/local/bin/xdg-open
zeninf "$finishmsg"

