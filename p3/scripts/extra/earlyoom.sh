#!/bin/bash
# name: EarlyOOM
# version: 1.0
# description: earlyoom_desc
# icon: preload.svg
# nocontainer
# repo: https://github.com/rfjakob/earlyoom
# optimized-only: yes
# compat: !solus, !fedora, !ostree, !ublue

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
if is_rhel; then
    pkg_install systemd-oomd
    sysd_enable systemd-oomd.service
else
    earlyoom_lib
fi
zeninf "$msg036"