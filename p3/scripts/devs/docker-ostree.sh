#!/bin/bash
# name: Docker
# version: 1.0
# description: docker_desc
# icon: docker
# compat: ostree, ublue

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
if zenity --question --title "Docker + Portainer CE Setup" --text "This will install Docker Engine and Portainer CE to manage it through a web UI. Proceed?" --width 360 --height 300; then
    cd $HOME
    sudo_rq
    curl -O https://download.docker.com/linux/fedora/docker-ce.repo
    sudo install -o 0 -g 0 -m644 docker-ce.repo /etc/yum.repos.d/docker-ce.repo
    rm docker-ce.repo
    _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
    _install_
    sudo systemctl enable --now docker
    sudo systemctl enable --now docker.socket
    sudo usermod -aG docker $USER
    sudo docker volume create portainer_data
    sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts
    zeninf "Setup complete. Your Portainer dashboard will open in your web browser now."
    xdg-open https://localhost:9443
    exit 0
fi