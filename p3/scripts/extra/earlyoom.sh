#!/bin/bash
# name: EarlyOOM
# version: 1.0
# description: earlyoom_desc
# icon: preload.svg
# nocontainer
# repo: https://github.com/rfjakob/earlyoom
# optimized-only: yes
# compat: !solus, !fedora, !ostree, !ublue, !ubuntu
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
if is_rhel; then
    pkg_install systemd-oomd
    sysd_enable systemd-oomd.service
else
    prep_tmp_noram
    if is_solus; then
        git clone https://github.com/rfjakob/earlyoom.git
        cd earlyoom
        sudo eopkg install -c system.devel
        sudo make install
    else
        pkg_install earlyoom
    fi
    fetch_from_mirror "earlyoom" \
        "https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/earlyoom" \
        "https://git.linux.toys/psygreg/linuxtoys/raw/branch/master/resources/earlyoom"
    if [ -f /etc/default/earlyoom ]; then
        prep_edit /etc/default/earlyoom
    else
        prep_create /etc/default/earlyoom
    fi
    copy_ -f earlyoom /etc/default/
    sysd_enable earlyoom
    unset _packages
fi
zeninf "$msg036"