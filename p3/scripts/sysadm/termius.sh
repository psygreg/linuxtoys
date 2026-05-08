#!/bin/bash
# name: Termius
# version: 1.0
# description: termius_desc
# icon: termius.png
# repo: https://termius.com/
# compat: debian, ubuntu, fedora, arch, suse

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat com.termius.Termius
zeninf "$msg018"
