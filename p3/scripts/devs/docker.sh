#!/bin/bash
# name: Docker
# version: 1.0
# description: docker_desc
# icon: docker.svg
# nocontainer
# reboot: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# functions
docker_in () { # install docker
    cd $HOME
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
            curl -O https://download.docker.com/linux/fedora/docker-ce.repo
            sudo install -o 0 -g 0 -m644 docker-ce.repo /etc/yum.repos.d/docker-ce.repo
            rm docker-ce.repo
        else
            sudo dnf -y install dnf-plugins-core
            sudo dnf-3 config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        fi
        _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
        if command -v rpm-ostree &> /dev/null; then
            _packages+=(podman-compose) # podman-compose is needed for rootless mode with ostree. the reasons for this are unknown, but without this it won't work at all.
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        _packages=(docker docker-compose)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        _packages=(docker docker-compose)
    fi
    _install_
    # fix for ostree
    # fix for ostree & ensure everything is set up correctly with docker
    if command -v rpm-ostree &> /dev/null; then
        sudo su -c 'echo "$(getent group docker)" >> /etc/group'
        sudo_rq # request another sudo to continue as it will be lost after su
    fi
    # enable rootless
    sudo usermod -aG docker $USER
    # enable services
    sudo systemctl enable --now docker
    sudo systemctl enable --now docker.socket
    sleep 2
}

if zenity --question --title "Docker" --text "This will install Docker Engine. Proceed?" --width 360 --height 300; then
    sudo_rq
    docker_in
    zeninf "Setup complete. You may install Portainer CE to manage Docker after rebooting."
    exit 0
fi