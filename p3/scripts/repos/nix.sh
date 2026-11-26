#!/bin/bash
# name: Nix Packages
# version: 1.2
# description: nixpkgs_desc
# icon: nix.svg
# compat: arch, cachy, fedora, debian, ubuntu, suse
# repo: https://github.com/NixOS/nixpkgs
# revert: arch, cachy, fedora
# systemd: yes
# architectures: x86_64, aarch64
# requires-script-api: 1

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
elif is_fedora; then
	# Fedora 43+ ships Nix as official packages. Use the multiuser daemon
	# setup recommended upstream; the packages provide the shell profile
	# integration under /etc/profile.d for new login shells.
	pkg_install nix nix-daemon || die "Failed to install Nix"
	sysd_enable nix-daemon.service
	sysd_start nix-daemon.service
else
	sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --no-daemon && {
		[ -f ~/.bashrc ] && { prep_edit ~/.bashrc && \
			echo -e "\nsource \${HOME}/.nix-profile/etc/profile.d/nix.sh" >> ~/.bashrc;
		}
	}
fi

# Nix packages' bubblewrap wrappers bind /etc/zoneinfo. Some distributions
# keep tzdata only under /usr/share/zoneinfo, so link it for Nix applications.
# NixOS and gregOS provide the path themselves and are skipped by the helper.
nix_available && {
	_nix_ensure_zoneinfo || zenwrn "Could not create the /etc/zoneinfo compatibility link."
}
