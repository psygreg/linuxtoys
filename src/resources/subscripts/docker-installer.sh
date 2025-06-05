#!/bin/bash
# functions

# check dependencies
dep_check () {

    local dependencies=()
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        dependencies=(newt)
    elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
        dependencies=(libnewt)
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        dependencies=(whiptail)
    fi
    depchecker_lib

}

# install docker and portainer CE
docker_in () {

    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            sudo zypper in docker -y
        else
            sudo dnf in docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
        sudo pacman -S --noconfirm docker
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        sudo apt install -y docker.io
    fi
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo docker volume create portainer_data
    sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
dep_check
if whiptail --title "Docker + Portainer CE Setup" --yesno "This will install Docker Engine and Portainer CE to manage it through a web UI. Proceed?" 8 78; then
    docker_in
    whiptail --title "Docker + Portainer CE Setup" --msgbox "Setup complete. You can acess your Portainer dashboard at https://localhost:9443" 8 78
    exit 0
fi