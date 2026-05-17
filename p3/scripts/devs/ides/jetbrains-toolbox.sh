#!/bin/bash
# name: JetBrains Toolbox
# version: 1.0
# description: jbtb_desc
# icon: jetbrains-toolbox.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
PKG_NAM="jetbrains-toolbox"
PKG_DIR="${HOME}/.local/${PKG_NAM}"

if [ -d "${PKG_DIR}" ]; then
	rm -rf "${PKG_DIR}" || { exit 1; }
fi

prep_dir "${PKG_DIR}"
PKG_URL="$(curl -fsSL 'https://data.services.jetbrains.com/products/releases?code=TBA&latest=true&type=release' | grep -Pio '"linux":\{"link":"\K[^"]+')"

curl -fsSL "${PKG_URL}" -o- | tar -xzvf - --strip-components=2 --one-top-level="${PKG_DIR}" && {
	(
		## .desktop file
		sed -i "/^Exec=/s|^.*$|Exec=${PKG_DIR}/${PKG_NAM}|" "${PKG_DIR}/${PKG_NAM}.desktop";

		# GNOME may show a generic package icon when Icon= is not resolvable.
		# Force desktop entry to use an absolute icon path from the extracted app files.
		JB_ICON="$(
			find "${PKG_DIR}" -maxdepth 2 -type f \
				\( -iname "*toolbox*.png" -o -iname "*toolbox*.svg" \) \
				| head -n 1
		)"
		if [ -n "$JB_ICON" ]; then
			if grep -q "^Icon=" "${PKG_DIR}/${PKG_NAM}.desktop"; then
				sed -i "/^Icon=/s|^.*$|Icon=${JB_ICON}|" "${PKG_DIR}/${PKG_NAM}.desktop"
			else
				printf "\nIcon=%s\n" "$JB_ICON" >> "${PKG_DIR}/${PKG_NAM}.desktop"
			fi
		fi
		prep_create "${HOME}/.local/share/applications/${PKG_NAM}.desktop"
		install -Dvm 0644 "${PKG_DIR}/${PKG_NAM}.desktop" "${HOME}/.local/share/applications/${PKG_NAM}.desktop";
		chmod +x "${HOME}/.local/share/applications/${PKG_NAM}.desktop";
	) && { zeninf "$msg018"; }
} || { exit 1; }
