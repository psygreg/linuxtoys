#!/bin/bash
# name: Oh My Bash
# version: 1.0
# description: Framework for managing your bash configuration.
# icon: ohmybash.png

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

_OSH=${OSH:-~/.oh-my-bash}
[ -d ${_OSH} ] && {
	zenity --question \
	--title "You already have Oh My Bash installed." \
	--text "Would you like to uninstall?" \
	--width 360 --height 300 && {
		yes | "${_OSH}"/tools/uninstall.sh && { zeninf "$msg018"; }
	}
	exit 0;
}

bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)" --unattended && {	zeninf "$msg018"; } || { fatal "Installation failure"; }
