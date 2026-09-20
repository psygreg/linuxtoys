#!/bin/bash
# name: Oh My Zsh
# version: 1.0
# description: omz_desc
# icon: zsh.png
# compat: arch, debian, fedora, ubuntu, !cachy, suse, ostree, rhel
# repo: https://ohmyz.sh
# compat: !steamos

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install zsh
if [ -f "$HOME/.zshrc" ]; then
    prep_edit "$HOME/.zshrc"
else
    prep_create "$HOME/.zshrc"
fi
(
	sh -c "$(curl -fsSL https://install.ohmyz.sh/) --unattended" && {
		shell_change "$(type -p zsh)";
	}
) && { info "$finishmsg"; } || die "Unable to complete installation"
