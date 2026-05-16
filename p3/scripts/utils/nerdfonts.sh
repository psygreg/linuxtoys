#!/bin/bash
# name: Nerd Fonts
# version: 1.0
# description: nerdfonts_desc
# icon: nerdfonts.svg
# repo: https://www.nerdfonts.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

_gh_user="ryanoasis"
_gh_repo="nerd-fonts"

mapfile -t _fonts < <(
	_vers=$(curl -fsSL https://github.com/${_gh_user}/${_gh_repo}/releases/latest -w '%{redirect_url}' -o /dev/null | awk -F'/' '{print $NF}')
	curl -fsSL https://github.com/${_gh_user}/${_gh_repo}/releases/expanded_assets/${_vers} | \
	grep -Pio '(?<=href=")([^"]+.tar.xz)'
)

_fonts_names=()
for url in "${_fonts[@]}"; do
	_url=${url##*/}
	_fonts_names+=(FALSE "${url}" "${_url%%.*}")
done

_select_font=($(zenity --list \
  --title="Choice your prefered nerd font" \
  --width=350 --height=500 \
  --column="Selected" --column="Link" --column="Fonts" \
  --hide-column=2 \
	--print-column=2 \
	--separator=$'\n' \
  --checklist --multiple \
  "${_fonts_names[@]}"))

[ -n "${_select_font}" ] && {
	(
		for _font_url in "${_select_font[@]}"; do
			_font_file=${_font_url##*/}
			_font_name=${_font_file%%.*}
			_font_path="$HOME/.local/share/fonts/${_font_name}"

			prep_dir "${_font_path}" # track for transmap
			rm -rf "${_font_path}" # ensure no overwriting conflict
			curl -fsSL "https://github.com${_font_url}" -o- | tar -xJf - -C "${_font_path}"
		done
		fc-cache -fv;
	) && { zeninf "$msg018"; } || { fatal "Nerd-Fonts installation unsuccessful"; }
} || {
	zenwrn "No font selected"
}
