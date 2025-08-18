#!/bin/bash
# name: Heroic Games Launcher
# version: 1.0
# description: hgl_desc
# icon: heroic
# nocontainer: ubuntu, debian, suse

# --- Start of the script code ---
tag=$(curl -s https://api.github.com/repos/Heroic-Games-Launcher/HeroicGamesLauncher/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
ver="${tag#v}"
if command -v rpm-ostree >/dev/null 2>&1 || [ "$ID" == "fedora" ] || [ "$ID_LIKE" == "fedora" ]; then
    sudo_rq
    if ! rpm -qi "heroic" 2>/dev/null; then
        if command -v rpm-ostree >/dev/null 2>&1; then
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
            rpm-ostree install -yA ./Heroic-${ver}-linux-x86_64.rpm || { echo "Heroic installation failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
            rm "Heroic-${ver}-linux-x86_64.rpm"
        else
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
            sudo dnf install -y ./Heroic-${ver}-linux-x86_64.rpm || { echo "Heroic installation failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
            rm "Heroic-${ver}-linux-x86_64.rpm"
        fi
    else
        # update if already installed
        hostver=$(rpm -qi "heroic" 2>/dev/null | grep "^Version" | awk '{print $3}')
        if [[ "$hostver" != "$ver" ]]; then
            if command -v rpm-ostree >/dev/null 2>&1; then
                wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
                rpm-ostree remove heroic
                rpm-ostree install -yA ./Heroic-${ver}-linux-x86_64.rpm || { echo "Heroic update failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
                rm "Heroic-${ver}-linux-x86_64.rpm"
            else
                wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
                sudo dnf remove -y heroic
                sudo dnf install -y ./Heroic-${ver}-linux-x86_64.rpm || { echo "Heroic update failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
                rm "Heroic-${ver}-linux-x86_64.rpm"
            fi
        else
            zeninf "$msg281" 
        fi
        unset hostver
    fi
elif [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    if ! pacman -Qi "heroic" 2>/dev/null 1>&2; then
        wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x64.pacman"
        sudo pacman -U --noconfirm ./Heroic-${ver}-linux-x64.pacman || { echo "Heroic installation failed"; rm -f "Heroic-${ver}-linux-x64.pacman"; return 1; }
        rm "Heroic-${ver}-linux-x64.pacman"
    else
        # update if already installed
        hostver=$(pacman -Q "heroic" 2>/dev/null | awk '{print $2}' | cut -d'-' -f1)
        if [[ "$hostver" != "$ver" ]]; then
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x64.pacman"
            sudo pacman -R --noconfirm heroic
            sudo pacman -U --noconfirm ./Heroic-${ver}-linux-x64.pacman || { echo "Heroic update failed"; rm -f "Heroic-${ver}-linux-x64.pacman"; return 1; }
            rm "Heroic-${ver}-linux-x64.pacman"
        else
            zeninf "$msg281" 
        fi
        unset hostver
    fi
else
    flatpak_in_lib
    flatpak install --or-update --user --noninteractive com.heroicgameslauncher.hgl
fi
unset tag
unset ver