#!/bin/bash
# name: SDKMAN
# version: 1.0
# description: sdkman_desc
# icon: sdkman.png
# repo: https://sdkman.io

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

sudo_rq
pkg_install zip unzip

[ -d ~/.sdkman ] && {
	zenity --question \
	--text "$rmmsg" \
	--width 360 --height 300 && {
		rm -rf ~/.sdkman && {
			(
				[ -f ~/.bashrc ] && prep_edit "$HOME/.bashrc" && sed -i '/SDKMAN TO WORK/,+2d' ~/.bashrc
				[ -f ~/.zshrc ] && prep_edit "$HOME/.zshrc" && sed -i '/SDKMAN TO WORK/,+2d' ~/.zshrc
			) && { zeninf "$msg018"; }
		}
	}
	exit 0;
}

curl -s "https://get.sdkman.io?ci=true" | bash && {	zeninf "$msg018"; } || { fatal "Installation failure"; }