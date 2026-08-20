#!/bin/bash
# name: Oracle VirtualBox
# version: 1.0
# description: vbox_desc
# icon: vbox.svg
# compat: debian, ubuntu, fedora, rhel, suse, ostree
# reboot: yes
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
askpass
echo "Installing and building kernel modules for VirtualBox. This may take a while..."
if is_ubuntu; then
    pkg_install gcc make "linux-headers-$(uname -r)" dkms
    pkg_install virtualbox virtualbox-dkms virtualbox-ext-pack virtualbox-qt
    secureboot_check
elif is_debian; then
    case "$VERSION_CODENAME" in
        bookworm|trixie)
            mydist="$VERSION_CODENAME"
            ;;
        *)
            mydist="trixie"
            ;;
    esac
    sudo tee /etc/apt/sources.list.d/virtualbox.sources >/dev/null <<EOF
Types: deb
URIs: https://download.virtualbox.org/virtualbox/debian
Suites: ${mydist}
Components: contrib
Architectures: amd64
Signed-By: /usr/share/keyrings/oracle-virtualbox-2016.gpg
EOF
    wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | sudo gpg --yes --output /usr/share/keyrings/oracle-virtualbox-2016.gpg --dearmor
    sudo apt update
    secureboot_check --ubuntumok
    pkg_install virtualbox
elif is_fedora || is_rhel || is_ostree; then
    rpmfusion_chk
    secureboot_check
    pkg_install VirtualBox akmods
elif is_suse; then
    case "$ID" in
        opensuse-tumbleweed)
            suse_repo="openSUSE_Tumbleweed"
            ;;
        opensuse-slowroll)
            suse_repo="openSUSE_Slowroll"
            ;;
        opensuse-leap)
            suse_repo="$VERSION_ID"
            ;;
        *)
            die "$incompatmsg"
            ;;
    esac
    sudo zypper --non-interactive addrepo "https://download.opensuse.org/repositories/Virtualization/${suse_repo}/Virtualization.repo"
    sudo zypper refresh
    pkg_install virtualbox-qt
else
    die "$incompatmsg"
fi
sudo usermod -aG vboxusers "$USER"
info "$rebootmsg"