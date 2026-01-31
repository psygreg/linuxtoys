#!/bin/bash
# name: Nix Packages
# version: 1.0
# description: nixpkgs_desc
# icon: nix.svg
# compat: fedora, arch, debian, ubuntu, cachy, suse
# repo: https://github.com/NixOS/nixpkgs

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq
if is_arch; then
	sudo pacman -S --noconfirm nix && {
		[ -f ~/.bashrc ] && {
			echo -e 'export PATH="$HOME/.nix-profile/bin:$PATH"' >> ~/.bashrc;
		}
		[ -f ~/.profile ] && {
			echo -e 'export XDG_DATA_DIRS="$HOME/.nix-profile/share:$XDG_DATA_DIRS"' >> ~/.profile;
		}
		[ -f ~/.bash_profile ] && {
			echo -e 'export XDG_DATA_DIRS="$HOME/.nix-profile/share:$XDG_DATA_DIRS"' >> ~/.bash_profile;
		}
	}
else
	sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon && {
		[ -f ~/.bashrc ] && {
			echo -e "\nsource \${HOME}/.nix-profile/etc/profile.d/nix.sh" >> ~/.bashrc;
		}
	}
fi