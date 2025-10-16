#!/bin/bash
# name: SDKMAN
# version: 1.0
# description: sdkman_desc
# icon: sdkman.png
# repo: https://sdkman.io

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
LT_PROGRAM="SDKMAN"

type -p zip unzip || {
	sudo_rq
	_packages=(zip unzip)
	_install_
}

[ -d ~/.sdkman ] && {
	zenity --question \
	--text "$rmmsg" \
	--width 360 --height 300 && {
		rm -rf ~/.sdkman && {
			(
				[ -f ~/.bashrc ] && { sed -i '/SDKMAN TO WORK/,+2d' ~/.bashrc; }
				[ -f ~/.zshrc ] && { sed -i '/SDKMAN TO WORK/,+2d' ~/.zshrc; }
			) && { zeninf "$msg018"; }
		}
	}
	exit 0;
}

curl -s "https://get.sdkman.io?ci=true" | bash && {	zeninf "$msg018"; } || { fatal "Installation failure"; }