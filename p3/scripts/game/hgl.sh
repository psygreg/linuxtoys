#!/bin/bash
# name: Heroic Games Launcher
# version: 1.0
# description: hgl_desc
# icon: heroic.svg
# nocontainer: ubuntu, debian, suse
# repo: https://heroicgameslauncher.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
tag=$(curl -s https://api.github.com/repos/Heroic-Games-Launcher/HeroicGamesLauncher/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
ver="${tag#v}"
if is_fedora || is_ostree; then
    sudo_rq
    prep_tmp
    if ! rpm -qi "heroic" 2>/dev/null; then
        if command -v rpm-ostree >/dev/null 2>&1; then
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
            pkg_fromfile ./Heroic-${ver}-linux-x86_64.rpm
        else
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
            pkg_fromfile ./Heroic-${ver}-linux-x86_64.rpm
        fi
    else
        # update if already installed
        hostver=$(rpm -qi "heroic" 2>/dev/null | grep "^Version" | awk '{print $3}')
        if [[ "$hostver" != "$ver" ]]; then
            if command -v rpm-ostree >/dev/null 2>&1; then
                wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
                sudo rpm-ostree remove heroic
                pkg_fromfile ./Heroic-${ver}-linux-x86_64.rpm
            else
                wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
                sudo dnf remove -y heroic
                pkg_fromfile ./Heroic-${ver}-linux-x86_64.rpm
            fi
        else
            zeninf "$msg281" 
        fi
        unset hostver
    fi
elif is_arch || is_cachy; then
    sudo_rq
    pkg_install heroic-games-launcher-bin
    zeninf "$msg281" 
else
    pkg_flat com.heroicgameslauncher.hgl
fi
unset tag
unset ver