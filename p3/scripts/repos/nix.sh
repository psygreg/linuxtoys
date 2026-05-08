#!/bin/bash
# name: Nix Packages
# version: 1.0
# description: nixpkgs_desc
# icon: nix.svg
# compat: fedora, arch, debian, ubuntu, cachy, suse
# repo: https://github.com/NixOS/nixpkgs
# revert: arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

sudo_rq
if is_arch || is_cachy; then
	pkg_install nix && {
		[ -f ~/.bashrc ] && { prep_edit ~/.bashrc && \
			echo -e 'export PATH="$HOME/.nix-profile/bin:$PATH"' >> ~/.bashrc;
		}
		[ -f ~/.profile ] && { prep_edit ~/.profile && \
			echo -e 'export XDG_DATA_DIRS="$HOME/.nix-profile/share:$XDG_DATA_DIRS"' >> ~/.profile;
		}
		[ -f ~/.bash_profile ] && { prep_edit ~/.bash_profile && \
			echo -e 'export XDG_DATA_DIRS="$HOME/.nix-profile/share:$XDG_DATA_DIRS"' >> ~/.bash_profile;
		}
	}
else
	sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon && {
		[ -f ~/.bashrc ] && { prep_edit ~/.bashrc && \
			echo -e "\nsource \${HOME}/.nix-profile/etc/profile.d/nix.sh" >> ~/.bashrc;
		}
	}
fi