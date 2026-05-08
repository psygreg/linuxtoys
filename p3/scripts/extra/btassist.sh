#!/bin/bash
# name: btrfs-Assistant
# version: 1.0
# description: btassist_desc
# icon: btassist.svg
# nocontainer
# compat: arch, cachy, fedora, suse, ubuntu, debian

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
    sudo_rq
    pkg_install btrfs-assistant snapper
else
    fatal "$msg220"
fi
