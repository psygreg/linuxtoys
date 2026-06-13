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
# functions
docker_in () { # install docker
    if is_ubuntu; then
        sudo apt install -y ca-certificates
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        { [ -n "$UBUNTU_CODENAME" ] && UBUCODENAME="$UBUNTU_CODENAME"; }
        { ([ "$VERSION_CODENAME" = "noble" ] || [ "$VERSION_CODENAME" = "resolute" ]) && UBUCODENAME="$VERSION_CODENAME"; }
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "${UBUCODENAME:-noble}") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif is_debian; then
        { [ "$VERSION_CODENAME" != "trixie" ] && [ "$VERSION_CODENAME" != "bookworm" ]; } && DEB_CODENAME="trixie" || DEB_CODENAME="$VERSION_CODENAME"
        sudo apt install -y ca-certificates # should not be declared as its removal may break the OS
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "${DEB_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
        sudo apt update
    elif is_fedora || is_ostree || is_rhel; then
        if command -v rpm-ostree &> /dev/null; then
            if ! rpm-ostree status | grep -q "docker-ce"; then
                fatal "$msg292"
            fi
        else
            sudo dnf -y install dnf-plugins-core # should not be declared as its removal may break the OS
            # Check dnf version to use appropriate config-manager syntax
            local dnf_version=$(rpm -qi dnf | grep "^Version" | awk '{print $3}')
            local dnf_major=$(echo "$dnf_version" | cut -d. -f1)
            { [ "$dnf_major" -lt 5 ] && sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo; } || sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
        fi
    fi
    { is_arch || is_cachy || is_suse || is_solus && pkg_install docker docker-compose; } || pkg_install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    # fix for ostree & ensure everything is set up correctly with docker
    if command -v rpm-ostree &> /dev/null; then
        sudo su -c 'echo "$(getent group docker)" >> /etc/group'
        sudo_rq # request another sudo to continue as it will be lost after su
    fi
    sudo usermod -aG docker $USER
    sysd_enable docker
    sysd_enable docker.socket
    sysd_start docker
    sysd_start docker.socket
    # firewalld fix for fedora
    if command -v firewalld &>/dev/null; then
        sudo firewall-cmd --zone=docker --change-interface=docker0
        sudo firewall-cmd --zone=docker --add-port=8006/tcp --permanent
        sudo firewall-cmd --zone=docker --add-port=3389/tcp --permanent
    fi
    # fix for apparmor.d users, leave only default profiles enabled
    if [ -f /etc/apparmor.d/dockerd ]; then
        prep_create /etc/apparmor.d/disable/dockerd
        sudo rm -f /etc/apparmor.d/disable/dockerd # ensure no issue with symlink
        sudo ln -s /etc/apparmor.d/dockerd /etc/apparmor.d/disable/
    fi
}
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
            docker_in
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