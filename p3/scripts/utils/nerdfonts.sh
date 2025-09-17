#!/bin/bash
# name: Nerd Fonts
# version: 1.0
# description: Iconic font aggregator, collection, and patcher.
# icon: nerdfonts.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/helpers.lib"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"

_gh_user="ryanoasis"
_gh_repo="nerd-fonts"

_fonts=($(
	_vers=$(curl https://github.com/${_gh_user}/${_gh_repo}/releases/latest -sw '%{redirect_url}' | awk -F'/' '{print $NF}')
	curl -fsSL https://github.com/${_gh_user}/${_gh_repo}/releases/expanded_assets/${_vers} | \
	grep -Pio '(?<=href=")([^"]+.tar.xz)')
)

_fonts_names=($(for url in ${_fonts[@]}; do _url=${url##*/}; printf 'FALSE %s %s ' "${url}" "${_url%%.*}"; done))

_select_font=($(zenity --list \
  --title="Choice your prefered nerd font" \
  --width=350 --height=500 \
  --column="Selected" --column="Link" --column="Fonts" \
  --hide-column=2 \
  --separator=" " \
  --checklist --multiple \
  "${_fonts_names[@]}"))

[ -n "${_select_font}" ] && {
	(
		for _font in "${_select_font[@]}"; do
			curl -fsSL "https://github.com/${_font}" -o- | tar -xvJf - --one-top-level="${HOME}/.local/share/fonts/";
		done;
		fc-cache -fv;
	) && { zeninf "Nerd-Fonts installed successfully"; } || { fatal "Nerd-Fonts installation unsuccessful"; }
} || {
	zenwrn "No font selected"
}
