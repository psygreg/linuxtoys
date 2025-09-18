#!/bin/bash
# name: LSW-WinBoat
# version: 1.0
# description: lsw_desc
# icon: lsw.svg
# reboot: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# functions
docker_in () { # install docker
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "ubuntu" ]; then
        _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
        sudo apt install -y ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif [ "$ID" == "debian" ]; then
        _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
        sudo apt install -y ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
            $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        if command -v rpm-ostree &> /dev/null; then
            if ! rpm-ostree status | grep -q "docker-ce"; then
                fatal "$msg292"
            fi
        else
            sudo dnf -y install dnf-plugins-core
            sudo dnf-3 config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        fi
        _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        _packages=(docker docker-compose)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        _packages=(docker docker-compose)
    fi
    _install_
    # fix for ostree & ensure everything is set up correctly with docker
    if command -v rpm-ostree &> /dev/null; then
        sudo echo "$(getent group docker)" >> /etc/group
    fi
    sudo usermod -aG docker $USER
    sudo systemctl enable --now docker
    sudo systemctl enable --now docker.socket
    # firewalld fix for fedora
    if command -v rpm-ostree &> /dev/null || command -v dnf &> /dev/null; then
        sudo firewall-cmd --zone=docker --change-interface=docker0
        sudo firewall-cmd --zone=docker --add-port=8006/tcp --permanent
        sudo firewall-cmd --zone=docker --add-port=3389/tcp --permanent
    fi
}
get_winboat () { # gets latest release
    local tag=$(curl -s "https://api.github.com/repos/TibixDev/winboat/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    local ver="${tag#v}"
    if command -v apt &> /dev/null; then
        if dpkg -s "winboat" &> /dev/null; then
            local hostver="$(dpkg -s winboat | grep -i Version | awk '{print $2}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        wget "https://github.com/TibixDev/winboat/releases/download/$tag/winboat-$ver-amd64.deb"
        sudo apt install -y "./winboat-$ver-amd64.deb"
    elif command -v dnf &> /dev/null || command -v zypper &> /dev/null || command -v rpm-ostree &> /dev/null; then
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
                sudo rpm-ostree remove winboat
            fi
            sudo rpm-ostree install "winboat-$ver-x86_64.rpm"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y "winboat-$ver-x86_64.rpm"
        elif command -v zypper &> /dev/null; then
            sudo zypper install -y "winboat-$ver-x86_64.rpm"
        fi
    elif command -v pacman &> /dev/null; then
        if pacman -Qi "winboat" &> /dev/null; then
            local hostver="$(pacman -Qi winboat | grep -i Version | awk '{print $3}')"
            if [ "$hostver" == "$ver" ]; then
                zeninf "$msg018"
                exit 0
            fi
        fi
        git clone https://aur.archlinux.org/winboat-bin.git
        cd winboat-bin || exit 1
        makepkg -i --noconfirm
    fi
}
# runtime
cd $HOME
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
            flatpak_in_lib
            flatpak install -y --user --noninteractive flathub com.freerdp.FreeRDP
            # enable iptables kernel module
            echo -e "ip_tables\niptable_nat" | sudo tee /etc/modules-load.d/iptables.conf
            # get latest winboat release
            get_winboat
            # cleanup
            cd ..
            rm -r lsw
            rm txtbox
            # request reboot for iptables module to load
            zeninf "$msg036"
        else # update
            mkdir -p lsw
            cd lsw || exit 1
            sudo_rq
            get_winboat
            cd ..
            rm -r lsw
            rm txtbox
            zeninf "$msg036"
        fi
    else
        rm txtbox
        exit 100
    fi
else
    fatal "$msg293"
fi