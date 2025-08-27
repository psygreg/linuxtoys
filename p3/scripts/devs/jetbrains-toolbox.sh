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

PKG_NAM="jetbrains-toolbox"
PKG_URL="$(curl -fsSL 'https://data.services.jetbrains.com/products/releases?code=TBA&latest=true&type=release' | grep -Pio '"linux":\{"link":"\K[^"]+')"

curl -fsSL "${PKG_URL}" -o- | tar -xzvf - --strip-components=2 --one-top-level="${HOME}/.local/${PKG_NAM}" && {
	(
		## .desktop file
		sed -i "/^Exec=/s|^.*$|Exec=${HOME}/.local/${PKG_NAM}/${PKG_NAM}|" ${HOME}/.local/${PKG_NAM}/${PKG_NAM}.desktop;
		install -Dvm 0644 ${HOME}/.local/${PKG_NAM}/${PKG_NAM}.desktop ${HOME}/.local/share/applications/${PKG_NAM}.desktop;
	) && { zeninf "$msg018"; }
} || { exit 1; }