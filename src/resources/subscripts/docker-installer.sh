#!/bin/bash
# functions

# check dependencies
dep_check () {

    local _packages=()
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        _packages=(newt)
    elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
        _packages=(libnewt)
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        _packages=(whiptail)
    fi
    _install_

}

# install docker and portainer CE
docker_in () {

    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            insta docker
        else
            insta docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        fi
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
        insta docker
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        insta docker.io
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
    title="Docker + Portainer CE Setup"
    msg="Setup complete. Your Portainer dashboard will open in your web browser now."
    _msgbox_
    xdg-open https://localhost:9443
    exit 0
fi