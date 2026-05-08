#!/bin/bash
# name: Distrobox-Adv
# version: 1.0
# description: Container do Debian via distrobox com pacotes que fornecem ambiente para uso de certificado digital por advogados no Brasil. Também inclui o Distroshelf.
# icon: boxadv.svg
# localize: pt
# repo: https://github.com/pedrohqb/distrobox-adv-br

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_fedora || is_ostree; then
    pkg_install distrobox podman pcsc-lite pcsc-lite-ccid
elif is_debian || is_ubuntu || is_solus; then
    if is_ubuntu; then
        sudo add-apt-repository ppa:michel-slm/distrobox -y
        sudo apt update
    fi
    pkg_install distrobox podman pcsc-lite ccid
elif is_arch || is_cachy; then
    pkg_install distrobox podman pcsclite ccid
elif is_suse || is_opensuse; then
    pkg_install distrobox podman pcsc-ccid
fi
sysd_enable pcscd.service
sysd_start pcscd.service
if is_ubuntu; then
    if distrobox-assemble create --file https://raw.githubusercontent.com/pedrohqb/distrobox-adv-br/refs/heads/main/distrobox-adv-br-legado; then
        distrobox_created distrobox-adv-br
    else
        fatal "Falha ao criar o container Distrobox-Adv."
    fi
else
    if distrobox-assemble create --file https://raw.githubusercontent.com/pedrohqb/distrobox-adv-br/refs/heads/main/distrobox-adv-br; then
        distrobox_created distrobox-adv-br
    else
        fatal "Falha ao criar o container Distrobox-Adv."
    fi
fi
pkg_flat com.ranfdev.DistroShelf
zeninf "$msg018"