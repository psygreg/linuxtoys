#!/bin/bash
# name: optivram
# description: optivram_desc
# icon: device.svg
# compat: fedora, arch
# gpu: Intel, AMD
# new
# systemd: yes

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_arch; then
    pkg_install dmemcg-booster 
    if [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        pkg_install plasma-foreground-booster-dmemcg
    fi
elif is_fedora; then
    prep_tmp
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/optivram/dmemcg-booster/dmemcg-booster-0.1.2-1.fc43.x86_64.rpm
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/optivram/plasma-foreground-booster/kcgroups-dmemcg-0.1-2.fc43.x86_64.rpm
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/optivram/plasma-foreground-booster/plasma-foreground-booster-dmemcg-0.1-2.fc43.x86_64.rpm
    pkg_fromfile dmemcg-booster-0.1.2-1.fc43.x86_64.rpm
    if [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        pkg_fromfile kcgroups-dmemcg-0.1-2.fc43.x86_64.rpm
        pkg_fromfile plasma-foreground-booster-dmemcg-0.1-2.fc43.x86_64.rpm
    fi
fi
zeninf "$rebootmsg" 