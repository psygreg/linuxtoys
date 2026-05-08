#!/bin/bash
# name: ZeroTier
# version: 1.0
# description: zerotier_desc
# icon: zerotier.png
# repo: https://github.com/zerotier/ZeroTierOne
# compat: fedora, ubuntu, debian, suse, arch, cachy
# revert: arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_

sudo_rq
if is_arch || is_cachy; then
	pkg_install zerotier-one
	if { sysd_enable zerotier-one && sysd_start zerotier-one; }; then
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
