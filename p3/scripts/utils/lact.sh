#!/bin/bash
# name: LACT
# version: 1.0
# description: lact_desc
# icon: device.svg
# repo: https://github.com/ilya-zlobintsev/LACT

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sudo_rq
pkg_flat io.github.ilya_zlobintsev.LACT
zeninf "$msg018"