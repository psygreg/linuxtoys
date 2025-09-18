#!/bin/bash
# name: Nix Packages
# version: 1.0
# description: Nix Packages
# icon: nix.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"

sudo_rq
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon && {
	[ -f ~/.bashrc ] && {
		echo -e "\nsource \${HOME}/.nix-profile/etc/profile.d/nix.sh" >> ~/.bashrc;
	}
}