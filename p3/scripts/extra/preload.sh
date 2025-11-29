#!/bin/bash
# name: Preload
# version: 1.0
# description: preload_desc
# icon: preload.svg
# compat: ubuntu, debian, fedora, ostree, ublue, cachy, arch
# reboot: ostree
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# RAM check
total_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
total_gb=$(( total_kb / 1024 / 1024 ))
_cram=$(( total_gb ))
# install only if user has enough RAM for preloading to not cause any issues
if (( _cram > 12 )); then
    if zenity --question --text "$msg208" --width 360 --height 300; then
        sudo_rq
        if [ "$ID" == "fedora" ] || [ "$ID" == "rhel" ] ||  [[ "$ID_LIKE" =~ "fedora" ]]; then
            if command -v rpm-ostree &>/dev/null; then
                cd $HOME
                wget https://copr.fedorainfracloud.org/coprs/elxreno/preload/repo/fedora-$(rpm -E %fedora)/elxreno-preload-fedora-$(rpm -E %fedora).repo
                sudo install -o 0 -g 0 elxreno-preload-fedora-$(rpm -E %fedora).repo /etc/yum.repos.d/elxreno-preload-fedora-$(rpm -E %fedora).repo
                rpm-ostree refresh-md
                rm elxreno-preload-fedora-$(rpm -E %fedora).repo
            else
                sudo dnf copr enable elxreno/preload -y
            fi
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            chaotic_aur_lib
        fi
        _packages=(preload)
        _install_
        sudo systemctl enable --now preload
        zeninf "$msg036"
    fi
else
    nonfatal "$msg228"
fi