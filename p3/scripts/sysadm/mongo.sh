#!/bin/bash
# name: Mon.goDB
# version: 8.3.0
# description: MongoDB database server
# icon: mongodb.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, rhel
# repo: https://github.com/mongodb/mongo
# revert: arch, cachy
# systemd: yes
# Removido updates redundates. #

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq

config_repo(){
    if is_rhel || is_fedora; then
        sudo tee /etc/yum.repos.d/mongodb-org-8.3.repo > /dev/null <<'EOF'
[mongodb-org-8.3]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/9/mongodb-org/8.3/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-8.0.asc
EOF
    elif is_suse; then
        sudo rpm --import https://pgp.mongodb.com/server-8.0.asc
        sudo zypper addrepo --gpgcheck \
            "https://repo.mongodb.org/zypper/suse15/mongodb-org/8.3/x86_64/" \
            mongodb-org-8.3
    elif is_ubuntu || is_debian; then
        pkg_install gnupg curl
        curl -fsSL https://pgp.mongodb.com/server-8.0.asc | \
            sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu ${VERSION_CODENAME:-noble}/mongodb-org/8.3 multiverse" | \
            sudo tee /etc/apt/sources.list.d/mongodb-org-8.3.list
    fi
}

install_mongodb(){
    if is_arch || is_cachy; then
        pkg_install mongodb
    elif is_rhel || is_fedora; then
        config_repo
        pkg_install mongodb-org
    elif is_suse; then
        config_repo
        pkg_install mongodb-org
    elif is_ubuntu || is_debian; then
        config_repo
        pkg_install mongodb-org
    fi
}

install_mongodb
sysd_enable mongod
sysd_start mongod
zeninf "$msg018"
