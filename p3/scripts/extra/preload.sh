#!/bin/bash
# name: Preload
# version: 1.0
# description: preload_desc
# icon: preload.svg
# compat: debian, cachy, arch
# reboot: ostree
# noconfirm: yes
# nocontainer
# systemd: yes

# --- Start of the script code ---
# RAM requirement in GB. msg228 (all languages) is baked by _lang_ from this
# value at lib-source time, and the check below enforces it: keep this line
# above the linuxtoys.lib source so one knob drives both the check and every
# translation of the requirement message.
_cram=8
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# RAM check
total_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
total_gb=$(( total_kb / 1024 / 1024 ))
# install only if user has enough RAM for preloading to not cause any issues
if (( total_gb > _cram )); then
    if zenity --question --text "$msg208" --width 360 --height 300; then
        sudo_rq
        if [ "$ID" == "fedora" ] || [ "$ID" == "rhel" ] ||  [[ "$ID_LIKE" =~ "fedora" ]]; then
            if is_ostree; then
                prep_tmp
                wget https://copr.fedorainfracloud.org/coprs/elxreno/preload/repo/fedora-$(rpm -E %fedora)/elxreno-preload-fedora-$(rpm -E %fedora).repo
                sudo install -o 0 -g 0 elxreno-preload-fedora-$(rpm -E %fedora).repo /etc/yum.repos.d/elxreno-preload-fedora-$(rpm -E %fedora).repo
                rpm-ostree refresh-md
            else
                sudo dnf copr enable elxreno/preload -y
            fi
        fi
        pkg_install --ostreecheck preload
        sysd_enable preload
        sysd_start preload
        zeninf "$msg036"
    fi
else
    nonfatal "$msg228"
fi
