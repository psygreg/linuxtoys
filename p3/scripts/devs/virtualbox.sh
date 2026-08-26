#!/bin/bash
# name: Oracle VirtualBox
# version: 1.0
# description: vbox_desc
# icon: vbox.svg
# compat: debian, ubuntu, fedora, rhel, suse, ostree
# reboot: yes

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
askpass

echo "Installing and building kernel modules for VirtualBox. This may take a while..."
if is_ubuntu || is_debian; then
    if is_ubuntu; then
        case "$UBUNTU_CODENAME" in
            noble|resolute)
                mydist="$UBUNTU_CODENAME"
                ;;
            *)
                mydist="noble"
                ;;
        esac
    else
        case "$VERSION_CODENAME" in
            bookworm|trixie)
                mydist="$VERSION_CODENAME"
                ;;
            *)
                mydist="trixie"
                ;;
        esac
    fi

    pkg_install gcc make "linux-headers-$(uname -r)" dkms
    prep_tmp
    # Oracle VirtualBox repository signing key
    wget -qO- https://www.virtualbox.org/download/oracle_vbox_2016.asc |
        sudo gpg --yes \
            --dearmor \
            --output /usr/share/keyrings/oracle-virtualbox-2016.gpg ||
        die "Failed to install VirtualBox repository key."
    # Oracle VirtualBox repository
    prep_create /etc/apt/sources.list.d/virtualbox.sources
    sudo tee /etc/apt/sources.list.d/virtualbox.sources >/dev/null <<EOF
Types: deb
URIs: https://download.virtualbox.org/virtualbox/debian
Suites: ${mydist}
Components: contrib
Architectures: amd64
Signed-By: /usr/share/keyrings/oracle-virtualbox-2016.gpg
EOF
    sudo apt update || die "Failed to update package lists."

    vbox_latest="$(
        curl -fsSL https://download.virtualbox.org/virtualbox/LATEST-STABLE.TXT
    )" ||
        die "Failed to determine latest VirtualBox version."
    vbox_series="${vbox_latest%.*}"
    vbox_pkg="virtualbox-${vbox_series}"
    if ! apt-cache show "$vbox_pkg" >/dev/null 2>&1; then
        die "VirtualBox ${vbox_series} is not available for ${mydist}."
    fi

    secureboot_check --ubuntumok
    pkg_install "$vbox_pkg"

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