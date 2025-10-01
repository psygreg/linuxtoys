#!/bin/bash
# name: SDKMAN
# version: 1.0
# description: The Software Development Kit Manager
# icon: sdkman.png

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

type -p zip unzip || {
	sudo_rq
	_packages=(zip unzip)
	_install_
}

[ -d ~/.sdkman ] && {
	zenity --question \
	--title "You already have SDKMAN installed." \
	--text "Would you like to uninstall?" \
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