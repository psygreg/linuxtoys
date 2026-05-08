#!/bin/bash
# name: Ananicy-cpp
# version: 1.0
# description: ananicy_desc
# icon: optimizer.svg
# compat: arch, fedora

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_arch; then
    pkg_install ananicy-cpp cachyos-ananicy-rules-git
    sysd_enable ananicy-cpp.service
elif is_fedora; then
    sudo dnf copr enable bieszczaders/kernel-cachyos-addons
    pkg_install ananicy-cpp cachyos-ananicy-rules
    sysd_enable ananicy-cpp.service
fi
zeninf "$rebootmsg" # while rebooting is not necessary, it is still recommended.
