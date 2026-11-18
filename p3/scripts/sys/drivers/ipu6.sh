#!/bin/bash
# name: Intel IPU6 Camera
# version: 1.0
# description: ipu6_desc
# icon: intel.png
# reboot: yes
# compat: fedora, debian, ubuntu, arch, cachy
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# Uses the open-source stack that ships with the distributions:
# in-kernel intel-ipu6 driver (Linux 6.10+) + libcamera software ISP (0.3+)
# + PipeWire libcamera plugin. No DKMS/akmod modules are installed.

: "${ipu6_none:=No Intel IPU6 camera controller was found in this computer. USB webcams already work without this.}"
: "${ipu6_kernel_old:=Your kernel is too old for the open-source IPU6 driver. Linux 6.10 or newer is required; update your system and try again. Running kernel:}"
: "${ipu6_libcamera_old:=The libcamera version in your distribution repositories is too old (0.3 or newer is required). Upgrade to a newer release, e.g. Debian 13 or Ubuntu 24.10+, and try again. Available version:}"
: "${ipu6_conflict:=An out-of-tree or proprietary IPU6 camera stack is installed. Mixing it with the open-source stack breaks the camera, so nothing was changed. Remove it first, or keep using it. Found:}"
: "${ipu6_done:=The open-source IPU6 camera stack is installed. Reboot, then use the camera in applications that access cameras through PipeWire (Firefox, GNOME Snapshot, OBS). In Chrome/Chromium, enable chrome://flags/#enable-webrtc-pipewire-camera. Cameras found now:}"
: "${ipu6_nofw:=The IPU6 firmware is missing and the firmware-misc-nonfree package is not available. Enable the non-free-firmware component in your APT sources, then try again.}"
: "${ipu6_nocam:=none yet. If the camera still does not appear after rebooting, its sensor is not supported by the mainline kernel yet.}"

# IPU6 PCI IDs from the kernel's include/media/ipu6-pci-table.h
# (TGL, JSL, ADL-P, ADL-N, RPL-P, MTL). IPU7/IPU8 are not handled here.
IPU6_IDS=" 0x9a19 0x4e19 0x465d 0x462e 0xa75d 0x7d19 "

ipu6_detect () {
    local dev
    for dev in /sys/bus/pci/devices/*; do
        [[ -r "$dev/vendor" && -r "$dev/device" ]] || continue
        [[ "$(<"$dev/vendor")" == "0x8086" ]] || continue
        [[ "$IPU6_IDS" == *" $(<"$dev/device") "* ]] && return 0
    done
    return 1
}

# version_ge A B: true when A >= B
version_ge () {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

ipu6_kernel_check () {
    local kver
    kver=$(uname -r | cut -d- -f1)
    version_ge "$kver" "6.10" || fatal "$ipu6_kernel_old $(uname -r)"
}

# Debian 12 / Ubuntu 24.04 ship libcamera without the software ISP
ipu6_libcamera_check () {
    local cand
    if is_debian || is_ubuntu; then
        cand=$(apt-cache policy libcamera-ipa 2>/dev/null | awk '/Candidate:/ { print $2 }')
        cand="${cand#*:}"
        [ -n "$cand" ] && [ "$cand" != "(none)" ] || fatal "$ipu6_libcamera_old (none)"
        version_ge "${cand%%-*}" "0.3" || fatal "$ipu6_libcamera_old $cand"
    fi
}

# refuse to mix with DKMS/akmod drivers or the Intel proprietary HAL
ipu6_conflict_check () {
    local found=()
    if command -v dkms &>/dev/null; then
        dkms status 2>/dev/null | grep -qiE 'ipu6|ivsc|usbio' && found+=("dkms: $(dkms status 2>/dev/null | grep -iE 'ipu6|ivsc|usbio' | cut -d, -f1 | sort -u | tr '\n' ' ')")
    fi
    if command -v rpm &>/dev/null; then
        rpm -qa 2>/dev/null | grep -qiE '^(akmod-intel-ipu6|kmod-intel-ipu6|ipu6-camera-hal)' && found+=("rpm: $(rpm -qa 2>/dev/null | grep -iE '^(akmod-intel-ipu6|kmod-intel-ipu6|ipu6-camera-hal)' | tr '\n' ' ')")
    fi
    if command -v pacman &>/dev/null; then
        pacman -Qq 2>/dev/null | grep -qiE '^intel-ipu6.*-dkms|^ipu6-camera-hal' && found+=("pacman: $(pacman -Qq 2>/dev/null | grep -iE '^intel-ipu6.*-dkms|^ipu6-camera-hal' | tr '\n' ' ')")
    fi
    if command -v dpkg-query &>/dev/null; then
        dpkg-query -W -f='${Package} ${Status}\n' 'libcamhal*' 'gst-plugins-icamera' 'intel-ipu6-dkms' 2>/dev/null | grep -q ' installed$' \
            && found+=("apt: $(dpkg-query -W -f='${Package} ${Status}\n' 'libcamhal*' 'gst-plugins-icamera' 'intel-ipu6-dkms' 2>/dev/null | awk '/ installed$/ { print $1 }' | tr '\n' ' ')")
    fi
    command -v v4l2-relayd &>/dev/null && systemctl is-enabled v4l2-relayd &>/dev/null && found+=("v4l2-relayd")
    (( ${#found[@]} == 0 )) || fatal "$ipu6_conflict ${found[*]}"
}

ipu6_firmware_present () {
    compgen -G "/lib/firmware/intel/ipu/ipu6*_fw.bin*" >/dev/null \
        || compgen -G "/usr/lib/firmware/intel/ipu/ipu6*_fw.bin*" >/dev/null \
        || compgen -G "/lib/firmware/intel/ipu6*_fw.bin*" >/dev/null
}

# Debian keeps the firmware in the non-free-firmware component
ipu6_firmware_check () {
    is_debian || return 0
    ipu6_firmware_present && return 0
    apt-cache policy firmware-misc-nonfree 2>/dev/null | awk '/Candidate:/ { print $2 }' | grep -qv '(none)' \
        || fatal "$ipu6_nofw"
}

ipu6_install () {
    local -a pkgs=()
    if is_fedora; then
        pkgs=(pipewire-plugin-libcamera libcamera-ipa libcamera-tools intel-vsc-firmware)
        ipu6_firmware_present || pkgs+=(linux-firmware)
    elif is_debian || is_ubuntu; then
        pkgs=(libspa-0.2-libcamera libcamera-ipa libcamera-tools)
        if ! ipu6_firmware_present; then
            { is_debian && pkgs+=(firmware-misc-nonfree); } || pkgs+=(linux-firmware)
        fi
    elif is_arch || is_cachy; then
        pkgs=(pipewire-libcamera libcamera-ipa libcamera-tools)
        ipu6_firmware_present || pkgs+=(linux-firmware-intel)
    fi
    pkg_install "${pkgs[@]}"
}

ipu6_detect || { info "$ipu6_none"; exit 100; }
ipu6_kernel_check
ipu6_conflict_check
ipu6_libcamera_check
ipu6_firmware_check
sudo_rq
ipu6_install
# load the drivers now when possible; a reboot completes the setup either way
sudo_ modprobe intel_ipu6_isys &>/dev/null || true
systemctl --user restart wireplumber &>/dev/null || true

cams=$(cam --list 2>/dev/null | sed -n 's/^[0-9]*: //p' | paste -sd ',')
zeninf "$ipu6_done ${cams:-$ipu6_nocam}"
