#!/bin/bash
# name: Thumbnailer
# version: 1.0
# description: thumb_desc
# icon: handbrake.svg
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
if [ ! -f $HOME/.local/.autopatch.state ]; then
    _packages=(ffmpegthumbnailer)
    sudo_rq
    _install_
    zeninf $"Operations completed."
else
    fatal $"This system has already been optimized by LinuxToys. To re-apply, please use the 'Undo Optimizations' script first."
fi