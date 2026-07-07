#!/bin/bash
# name: Docker
# version: 1.0
# description: docker_desc
# icon: docker.svg
# nocontainer
# reboot: yes
# compat: !ublue
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# functions
docker_in () { # install docker
    prep_tmp
    if is_ubuntu; then
        pkg_remove docker.io docker-compose docker-compose-v2 docker-doc podman-docker
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
        pkg_remove docker.io docker-compose docker-doc podman-docker
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
            pkg_remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-selinux docker-engine-selinux docker-engine
            curl -O https://download.docker.com/linux/fedora/docker-ce.repo
            sudo install -o 0 -g 0 -m644 docker-ce.repo /etc/yum.repos.d/docker-ce.repo
            pkg_install podman-compose # podman-compose is needed for rootless mode with ostree. the reasons for this are unknown, but without this it won't work at all.
        else
            { is_rhel && pkg_remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine; } || pkg_remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-selinux docker-engine-selinux docker-engine
            sudo dnf -y install dnf-plugins-core # should not be declared as its removal may break the OS
            # Check dnf version to use appropriate config-manager syntax
            { command -v "dnf5" &>/dev/null && sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo; } || sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
        fi
    fi
    { ( is_arch || is_cachy || is_suse || is_solus ) && pkg_install docker docker-compose; } || pkg_install --ostreecheck docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
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

sudo_rq
docker_in
zeninf "$rebootmsg"
