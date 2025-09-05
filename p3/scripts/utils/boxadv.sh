#!/bin/bash
# name: Distrobox-Adv
# version: 1.0
# description: Container do Debian via distrobox com pacotes que fornecem ambiente para uso de certificado digital por advogados no Brasil. Também inclui o Distroshelf.
# icon: boxadv.svg
# localize: pt

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
if [ "$ID" == "fedora" ] || [ "$ID" == "rhel" ] ||  [[ "$ID_LIKE" =~ "fedora" ]]; then
    _packages=(distrobox podman pcsc-lite pcsc-lite-ccid)
elif [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ] || [[ "$ID_LIKE" =~ "debian" ]] || [[ "$ID_LIKE" =~ "ubuntu" ]]; then
    _packages=(distrobox podman pcsc-lite ccid)
elif [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] ||[[ "$ID_LIKE" =~ "arch" ]]; then
    _packages=(distrobox podman pcsclite ccid)
elif [ "$ID" = "suse" ] || [[ "$ID" =~ "opensuse" ]] || [[ "$ID_LIKE" =~ "suse" ]]; then
    _packages=(distrobox podman pcsc-ccid)
fi
_install_ 
sudo systemctl enable --now pcscd.service
distrobox-assemble create --file https://raw.githubusercontent.com/pedrohqb/distrobox-adv-br/refs/heads/main/distrobox-adv-br
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.ranfdev.DistroShelf
zeninf $"Operations completed."