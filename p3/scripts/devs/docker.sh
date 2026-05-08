#!/bin/bash
# name: Docker
# version: 1.0
# description: docker_desc
# icon: docker.svg
# nocontainer
# reboot: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# functions
docker_in () { # install docker
    prep_tmp
    if is_debian || is_ubuntu; then
        sudo apt install -y ca-certificates # should not be declared as its removal may break the OS
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
            $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif is_debian; then
        sudo apt install -y ca-certificates # should not be declared as its removal may break the OS
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
            $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt update
    elif is_fedora; then
        if command -v rpm-ostree &> /dev/null; then
            curl -O https://download.docker.com/linux/fedora/docker-ce.repo
            sudo install -o 0 -g 0 -m644 docker-ce.repo /etc/yum.repos.d/docker-ce.repo
            pkg_install podman-compose # podman-compose is needed for rootless mode with ostree. the reasons for this are unknown, but without this it won't work at all.
        else
            sudo dnf -y install dnf-plugins-core # should not be declared as its removal may break the OS
            sudo dnf-3 config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        fi
    fi
    if is_arch || is_cachy || is_suse || is_solus; then
        pkg_install docker docker-compose
    else
        pkg_install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    _install_
    # fix for ostree & ensure everything is set up correctly with docker
    if command -v rpm-ostree &> /dev/null; then
        sudo su -c 'echo "$(getent group docker)" >> /etc/group'
        sudo_rq # request another sudo to continue as it will be lost after su
    fi
    # Ensure docker group exists before adding users (can be missing on some setups)
    if ! getent group docker >/dev/null 2>&1; then
        sudo groupadd docker
    fi
    # enable rootless
    sudo usermod -aG docker $USER
    # enable services
    sysd_enable docker
    sysd_enable docker.socket
}

if [[ "$DISABLE_ZENITY" == "1" ]] || zenity --question --title "Docker" --text "This will install Docker Engine. Proceed?" --width 360 --height 300; then
    sudo_rq
    docker_in
    zeninf "Setup complete. You may install Portainer CE to manage Docker after rebooting."
    exit 0
fi
