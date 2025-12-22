#!/bin/bash
# name: Fisher
# version: 1.0
# description: fisher_desc
# icon: fish.svg
# repo: https://github.com/jorgebucaran/fisher

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq
_packages=(fish)
_install_

if command -v fish >/dev/null 2>&1; then
	sudo chsh -s "$(type -p fish)" "$USER"

	if fish -c "curl -sL https://git.io/fisher | source; fisher install jorgebucaran/fisher"; then
		zeninf "$msg018"
	else
		fatal "Fisher could not be installed."
	fi
else
	fatal "Unable to complete installation"
fi