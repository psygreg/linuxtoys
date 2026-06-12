#!/bin/bash
# name: CPU ondemand
# version: 1.0
# description: ondemand_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, ostree, ublue, rhel
# reboot: yes
# nocontainer
# optimized-only: yes
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
if [ ! -f /etc/systemd/system/set-ondemand-governor.service ]; then
    pp_ondemand
fi
zeninf "$msg036"