#!/bin/bash
# name: OpenRazer
# version: 1.0
# description: oprzr_desc
# icon: gaming.svg
# compat: ublue
# nocontainer
# repo: https://openrazer.github.io
# revert: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
ujust install-openrazer
zeninf "$msg036"