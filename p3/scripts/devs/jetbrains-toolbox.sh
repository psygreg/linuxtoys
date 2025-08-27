#!/bin/bash
# name: JetBrains Toolbox
# version: 1.0
# description: jbtb_desc
# icon: jetbrains-toolbox.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
sudo_rq

PKG_NAM="jetbrains-toolbox"

_uninstall() {
	rm -rvf $HOME/.local/${PKG_NAM} && {
		(
			sudo rm -vf "/usr/local/share/applications/${PKG_NAM}.desktop"
			sudo unlink "/usr/local/bin/${PKG_NAM}"
		) && { exit 0; };
	}

	exit 0;
}

case "${1}" in
	remove)
		_uninstall
		;;
esac

PKG_URL="$(curl -fsSL 'https://data.services.jetbrains.com/products/releases?code=TBA&latest=true&type=release' | grep -Pio '"linux":\{"link":"\K[^"]+')"

curl -fsSL "${PKG_URL}" -o- | tar -xzvf - --strip-components=2 --one-top-level="$HOME/.local/${PKG_NAM}" && {
	(
		sudo install -Dm 0644 "$HOME/.local/${PKG_NAM}/${PKG_NAM}.desktop" "/usr/local/share/applications/${PKG_NAM}.desktop";
		sudo ln -v -s "$HOME/.local/${PKG_NAM}/${PKG_NAM}" "/usr/local/bin/";
	) && { zeninf "$msg018"; }
} || { exit 1; }