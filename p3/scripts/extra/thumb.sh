#!/bin/bash
# name: Thumbnailer
# version: 1.0
# description: thumb_desc
# icon: handbrake.svg
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if [ ! -f $HOME/.local/.autopatch.state ]; then
    sudo_rq
    pkg_install ffmpegthumbnailer
    zeninf "$msg018"
else
    fatal "$msg234"
fi