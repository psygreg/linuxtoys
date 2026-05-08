#!/bin/bash
# name: Input Remapper
# version: 1.0
# description: remapper_desc
# icon: input-remapper.png
# compat: fedora, arch, debian, ubuntu, cachy, ostree, solus
# nocontainer
# reboot: ostree
# repo: https://github.com/sezanzeb/input-remapper

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_arch || is_cachy; then
    pkg_install input-remapper-git
else
    pkg_install input-remapper
fi
zeninf "$msg018"