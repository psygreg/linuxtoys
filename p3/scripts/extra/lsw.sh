#!/bin/bash
# name: LSW-WinBoat
# version: 1.0
# description: lsw_desc
# icon: lsw.svg
# reboot: yes
# nocontainer
# compat: !ublue
# repo: https://github.com/TibixDev/winboat
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
get_winboat () { # gets latest release
    local tag=$(curl -s "https://api.github.com/repos/TibixDev/winboat/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    [ -z ${tag} ] && { fatal "It was not possible to obtain the latest available version of Winboat."; exit 1;}
    local ver="${tag#v}"
    if is_debian || is_ubuntu; then
        if dpkg -s "winboat" &> /dev/null; then
            local hostver="$(dpkg -s winboat | grep -i Version | awk '{print $2}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        wget "https://github.com/TibixDev/winboat/releases/download/$tag/winboat-$ver-amd64.deb"
        pkg_fromfile "winboat-$ver-amd64.deb"
    elif is_fedora || is_suse || is_rhel; then
        if rpm -qi "winboat" &> /dev/null; then
            local hostver="$(rpm -qi winboat | grep -i Version | awk '{print $3}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        wget "https://github.com/TibixDev/winboat/releases/download/$tag/winboat-$ver-x86_64.rpm"
        if command -v rpm-ostree &> /dev/null; then
            if rpm -qi "winboat" &> /dev/null; then
                pkg_remove winboat
            fi
        fi
        pkg_fromfile "winboat-$ver-x86_64.rpm"
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
# runtime
prep_tmp
sleep 1
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
    
if [ -e /dev/kvm ]; then
    if zenity --question --title "LSW" --text "$msg217" --height=300 --width=300; then
        if ! which winboat &> /dev/null; then
            mkdir -p lsw
            cd lsw || exit 1
            sudo_rq
            # stage 1: docker
            call_script docker
            # stage 2: freeRDP
            pkg_flat com.freerdp.FreeRDP
            # enable iptables kernel module
            if [ -f /etc/modules-load.d/iptables.conf ]; then
                prep_edit /etc/modules-load.d/iptables.conf
            else
                prep_create /etc/modules-load.d/iptables.conf
            fi
            echo -e "ip_tables\niptable_nat" | sudo tee /etc/modules-load.d/iptables.conf
            # get latest winboat release
            get_winboat
            # request reboot for iptables module to load
            zeninf "$msg036"
        else # update
            mkdir -p lsw
            cd lsw || exit 1
            sudo_rq
            get_winboat
            zeninf "$msg036"
        fi
    else
        exit 100
    fi
else
    fatal "$msg293"
fi