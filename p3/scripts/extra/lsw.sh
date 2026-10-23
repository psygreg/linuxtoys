#!/bin/bash
# name: LSW-WinBoat
# version: 1.0
# description: lsw_desc
# icon: lsw.svg
# reboot: yes
# nocontainer
# compat:
# repo: https://github.com/TibixDev/winboat
# systemd: yes
# wsl: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
[ ! -n "$UPD_SERVICE" ] && sudo_rq

# Resolves the latest WinBoat release tag and its version (tag without the
# leading "v") into $tag and $ver. Used by both the native and AppImage paths.
get_release () {
    local _tag
    _tag=$(curl -s "https://api.github.com/repos/winboat-org/winboat/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    [ -z "$_tag" ] && { fatal "It was not possible to obtain the latest available version of Winboat."; exit 1; }
    tag="$_tag"
    ver="${tag#v}"
}

# Podman backend (used on immutable hosts: ostree and SteamOS-family systems).
# WinBoat is distributed as an AppImage on these systems and talks to Windows
# through a Podman container instead of the Docker engine used by the native
# package installs.
get_winboat_appimage () {
    get_release
    prep_tmp_noram
    local appimage="winboat-$ver-x86_64.AppImage"
    wget "https://github.com/winboat-org/winboat/releases/download/$tag/$appimage" \
        || { fatal "It was not possible to download the Winboat AppImage."; exit 1; }
    pkg_appimage "./$appimage"
}

# FreeRDP and the iptables kernel modules are required by every backend, so
# this runs on both the native and the homebrew/podman paths.
freerdp_iptables_setup () {
    # freeRDP
    pkg_flat com.freerdp.FreeRDP
    # enable iptables kernel module
    if [ -f /etc/modules-load.d/iptables.conf ]; then
        prep_edit /etc/modules-load.d/iptables.conf
    else
        prep_create /etc/modules-load.d/iptables.conf
    fi
    echo -e "ip_tables\niptable_nat" | sudo tee /etc/modules-load.d/iptables.conf
}

get_winboat () { # gets latest release (native package paths)
    { is_arch || is_cachy; } || get_release
    if is_debian || is_ubuntu; then
        if dpkg -s "winboat" &> /dev/null; then
            local hostver="$(dpkg -s winboat | grep -i Version | awk '{print $2}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        wget "https://github.com/winboat-org/winboat/releases/download/$tag/winboat-$ver-amd64.deb"
        pkg_fromfile "./winboat-$ver-amd64.deb"
    elif is_fedora || is_suse || is_rhel; then
        if rpm -qi "winboat" &> /dev/null; then
            local hostver="$(rpm -qi winboat | grep -i Version | awk '{print $3}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        wget "https://github.com/winboat-org/winboat/releases/download/$tag/winboat-$ver-x86_64.rpm"
        if is_ostree; then
            if rpm -qi "winboat" &> /dev/null; then
                pkg_remove winboat
            fi
        fi
        pkg_fromfile "./winboat-$ver-x86_64.rpm"
    elif is_arch || is_cachy; then
        if pacman -Qi "winboat-bin" &> /dev/null; then
            local hostver="$(pacman -Qi winboat-bin | grep -i Version | awk '{print $3}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        pkg_install winboat-bin
    fi
}

if [ ! -e /dev/kvm ]; then
    die "$msg293"
fi

# warning box
prep_tmp_noram
{
    echo "$msg209"
    echo "$msg210"
    echo "$msg211"
    echo "$msg212"
    echo "$msg213"
    echo "$msg214"
    echo "$msg215"
    echo "$msg216"
} > txtbox

zenity --text-info \
    --title="LSW" \
    --filename=txtbox \
    --checkbox="$msg276" \
    --width=400 --height=360

if question "LSW" "$msg217"; then
    if is_ostree || is_steamos; then
        # Homebrew/podman backend: the container engine is provided by the host
        # or Homebrew, and WinBoat itself ships as an AppImage. No Docker engine
        # is needed here.
        askpass
        # stage 1: podman container backend
        if command -v podman &> /dev/null; then
            echo "Podman is already installed, using it as the Winboat backend."
        else
            pkg_brew podman
        fi
        # stage 2: podman-compose (from Homebrew) for the Winboat container stack
        pkg_brew podman-compose
        # stage 3: freeRDP + iptables kernel modules
        freerdp_iptables_setup
        # stage 4: Winboat AppImage
        get_winboat_appimage
    elif ! which winboat &> /dev/null; then
        askpass
        # stage 1: docker
        call_script docker
        # stage 2: freeRDP + iptables kernel modules
        freerdp_iptables_setup
        # get latest winboat release
        get_winboat
        # request reboot for iptables module to load
        info "$msg036"
    else # update
        askpass
        get_winboat
        info "$msg036"
    fi
else
    exit 100
fi
