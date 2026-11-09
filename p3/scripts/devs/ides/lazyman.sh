#!/bin/bash
# name: Lazyman
# version: 1.0
# description: lazyman_desc
# icon: lazyman.png
# compat: fedora, arch, cachy, ostree, ublue, suse, rhel
# repo: https://lazyman.dev

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

[ -f $HOME/.config/nvim-Lazyman/lazyman.sh ] && { zeninf "${msg281}"; exit 0; }

sudo_rq
pkg_install neovim
prep_dir "$HOME/.config/nvim-Lazyman"
git clone --depth=1 https://github.com/doctorfree/nvim-lazyman $HOME/.config/nvim-Lazyman
$HOME/.config/nvim-Lazyman/lazyman.sh -z && {
	_nvim_labels=("Abstract" "AstroNvimPlus" "Basic IDE" "Ecovim" "LazyVim" "LunarVim" "MagicVim" "NvChad" "SpaceVim")
	_nvim_ids=(g a j e l v m c s)
	_selected_nvim_label=$(radioselect --no-default --title "$msg006" "${_nvim_labels[@]}") || _selected_nvim_label=""
	_selected_nvim=""
	for _i in "${!_nvim_labels[@]}"; do
		[[ "${_nvim_labels[_i]}" == "$_selected_nvim_label" ]] && _selected_nvim="${_nvim_ids[_i]}"
	done

	[ -n "$_selected_nvim" ] && {
		$HOME/.config/nvim-Lazyman/lazyman.sh -${_selected_nvim} -z && {
			zeninf "$msg287";
			exit 0;
		}
	}

	zeninf "$msg175"
	exit 100
}