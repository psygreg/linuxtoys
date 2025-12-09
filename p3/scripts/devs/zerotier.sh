#!/bin/bash
# name: ZeroTier
# version: 1.0
# description: zerotier_desc
# icon: zerotier.png
# repo: https://github.com/zerotier/ZeroTierOne

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq

if is_arch || is_cachy; then
	_packages=(zerotier-one)
	_install_
	if sudo systemctl enable --now zerotier-one; then
		zeninf "ZeroTier installed successfully!"
	else
		fatal "Installation failed."
	fi
else
	if curl -fsSL https://install.zerotier.com | sudo bash; then
		zeninf "ZeroTier installed successfully!"
	else
		fatal "Installation failed."
	fi
fi