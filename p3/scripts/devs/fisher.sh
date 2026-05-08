#!/bin/bash
# name: Fisher
# version: 1.0
# description: fisher_desc
# icon: fish.svg
# repo: https://github.com/jorgebucaran/fisher

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
pkg_install fish
if command -v fish >/dev/null 2>&1; then
	shell_change "$(type -p fish)" "$USER"
	prep_edit "$HOME/.config/fish/config.fish"
	if fish -c "curl -sL https://git.io/fisher | source; fisher install jorgebucaran/fisher"; then
		zeninf "$msg018"
	else
		fatal "Fisher could not be installed."
	fi
else
	fatal "Unable to complete installation"
fi