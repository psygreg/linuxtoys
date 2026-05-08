#!/bin/bash
# name: Flatseal
# version: 1.0
# description: fseal_desc
# icon: flatseal.svg
# repo: https://github.com/tchx84/Flatseal

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat com.github.tchx84.Flatseal
zeninf "$msg018"