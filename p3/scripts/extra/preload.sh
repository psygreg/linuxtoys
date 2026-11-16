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
# Decimal GB minimum, shared by the check and translated messages. Preserve
# the existing documented 16 GB floor rather than adopting upstream's 8 GB.
_cram=16
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# MemTotal is KiB. Avoid truncation to GiB, malformed arithmetic, overflow and
# treating an absent measurement as permission to enable a memory-heavy daemon.
total_kb=$(awk '$1 == "MemTotal:" && $3 == "kB" { print $2; exit }' /proc/meminfo 2>/dev/null) || total_kb=""
if [[ ! $total_kb =~ ^[1-9][0-9]{0,11}$ ]]; then
    nonfatal "Unable to detect system RAM safely. Preload was not enabled."
    exit 1
fi
required_kb=$(( (_cram * 1000000000 + 1023) / 1024 ))
if (( total_kb >= required_kb )); then
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
