#!/bin/bash
# name: Lazyman
# version: 1.0
# description: lazyman_desc
# icon: lazyman.png
# compat: fedora, arch, cachy, ostree, ublue, suse
# repo: https://lazyman.dev

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

[ -f $HOME/.config/nvim-Lazyman/lazyman.sh ] && { zeninf "${msg281}"; exit 0; }

sudo_rq
_packages=(neovim git)
_install_

git clone --depth=1 https://github.com/doctorfree/nvim-lazyman $HOME/.config/nvim-Lazyman
$HOME/.config/nvim-Lazyman/lazyman.sh -z && {
	_nvims=(
		"FALSE" "g" "Abstract"
		"FALSE" "a" "AstroNvimPlus"
		"FALSE" "j" "Basic IDE"
		"FALSE" "e" "Ecovim"
		"FALSE" "l" "LazyVim"
		"FALSE" "v" "LunarVim"
		"FALSE" "m" "MagicVim"
		"FALSE" "c" "NvChad"
		"FALSE" "s" "SpaceVim"
	)

	_selected_nvim=$(zenity --list \
	--title="$msg006" \
	--width=420 --height=500 \
	--column="Selected" --column="Options" --column="NVIMS" \
	--hide-column=2 \
	--separator=" " \
	--radiolist \
	"${_nvims[@]}")

	[ -n "$_selected_nvim" ] && {
		$HOME/.config/nvim-Lazyman/lazyman.sh -${_selected_nvim} -z && {
			zeninf "$msg287";
			exit 0;
		}
	}

	zeninf "$msg175"
	exit 100
}