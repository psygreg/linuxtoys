#!/bin/bash
# functions

# install docker and portainer CE
docker_in () {

    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "ubuntu" ]; then
        local _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin dialog git iproute2 libnotify-bin)
        insta ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif [ "$ID" == "debian" ]; then
        local _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin dialog git iproute2 libnotify-bin)
        insta ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
            $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        sudo dnf -y install dnf-plugins-core
        sudo dnf-3 config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        local _packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin curl dialog git iproute libnotify)
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        local _packages=(docker docker-compose curl dialog git iproute2 libnotify)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        local _packages=(docker docker-compose curl dialog git iproute2 libnotify-tools)
    fi
    _install_
    sudo usermod -aG docker $USER
    sudo systemctl enable --now docker
    sleep 2
    sudo docker volume create portainer_data
    sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
dep_check
if whiptail --title "Docker + Portainer CE Setup" --yesno "This will install Docker Engine and Portainer CE to manage it through a web UI. Proceed?" 8 78; then
    docker_in
    title="Docker + Portainer CE Setup"
    msg="Setup complete. Your Portainer dashboard will open in your web browser now."
    _msgbox_
    xdg-open https://localhost:9443
    exit 0
fi
