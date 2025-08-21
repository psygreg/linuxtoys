#!/bin/bash
# name: Thumbnailer
# version: 1.0
# description: thumb_desc
# icon: handbrake.svg
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
. /etc/os-release
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
if [ ! -f $HOME/.local/.autopatch.state ]; then
    _packages=(ffmpegthumbnailer)
    sudo_rq
    _install_
    zeninf "$msg018"
else
    fatal "$msg234"
fi