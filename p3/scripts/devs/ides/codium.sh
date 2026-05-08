#!/bin/bash
# name: VSCodium
# version: 1.0
# description: codium_desc
# icon: vscodium.svg
# repo: https://vscodium.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_ubuntu || is_debian; then
    wget -qO - https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
    | gpg --dearmor \
    | sudo dd of=/usr/share/keyrings/vscodium-archive-keyring.gpg
    echo -e 'Types: deb\nURIs: https://download.vscodium.com/debs\nSuites: vscodium\nComponents: main\nArchitectures: amd64 arm64\nSigned-by: /usr/share/keyrings/vscodium-archive-keyring.gpg' \
    | sudo tee /etc/apt/sources.list.d/vscodium.sources
    pkg_install codium
elif is_fedora || is_ostree; then
    sudo tee -a /etc/yum.repos.d/vscodium.repo << 'EOF'
[gitlab.com_paulcarroty_vscodium_repo]
name=gitlab.com_paulcarroty_vscodium_repo
baseurl=https://paulcarroty.gitlab.io/vscodium-deb-rpm-repo/rpms/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg
metadata_expire=1h
EOF
    pkg_install codium
elif is_suse; then
    sudo tee -a /etc/zypp/repos.d/vscodium.repo << 'EOF'
[gitlab.com_paulcarroty_vscodium_repo]
name=gitlab.com_paulcarroty_vscodium_repo
baseurl=https://paulcarroty.gitlab.io/vscodium-deb-rpm-repo/rpms/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg
metadata_expire=1h
EOF
    pkg_install codium
elif is_arch || is_cachy; then
    pkg_install vscodium-bin
else
    pkg_flat com.vscodium.codium
    flatcodium="true"
fi
# patch for extensions
if [ -n "$flatcodium" ]; then
    prep_create "$HOME/.var/app/com.vscodium.codium/config/VSCodium/product.json"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/product.json -O "$HOME/.var/app/com.vscodium.codium/config/VSCodium/product.json"
else
    prep_create "$HOME/.config/VSCodium/product.json"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/product.json -O "$HOME/.config/VSCodium/product.json"
fi
zeninf "$msg018"