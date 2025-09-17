#!/bin/bash
# name: Oh My Zsh
# version: 1.0
# description: omz_desc
# icon: zsh.png
# compat: arch, debian, fedora, ubuntu, cachyos, suse

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"

sudo_rq
_packages=(zsh curl git)
_install_

(
	sh -c "$(curl -fsSL https://install.ohmyz.sh/) --unattended" && {
		sudo chsh -s "$(type -p zsh)" "$USER";	
	}
) && { zeninf "$msg018"; } || { fatal "Unable to complete installation"; }