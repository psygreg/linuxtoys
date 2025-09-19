#!/bin/bash
# name: Docker
# version: 1.0
# description: docker_desc
# icon: docker.svg
# nocontainer
# reboot: ostree

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
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        _packages=(docker docker-compose)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        _packages=(docker docker-compose)
    fi
    _install_
    # fix for ostree
    if command -v rpm-ostree &> /dev/null; then
        sudo echo "$(getent group docker)" >> /etc/group
    fi
    # enable rootless
    sudo usermod -aG docker $USER
    # enable services
    sudo systemctl enable --now docker
    sudo systemctl enable --now docker.socket
    sleep 2
    # portainer setup
    sudo docker volume create portainer_data
    sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts
}
if zenity --question --title "Docker + Portainer CE Setup" --text "This will install Docker Engine and Portainer CE to manage it through a web UI. Proceed?" --width 360 --height 300; then
    sudo_rq
    docker_in
    zeninf "Setup complete. Your Portainer dashboard will open in your web browser now."
    xdg-open https://localhost:9443
    exit 0
fi