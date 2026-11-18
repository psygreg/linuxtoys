#!/bin/bash
# name: Nerd Fonts
# version: 1.1
# description: nerdfonts_desc
# icon: nerdfonts.webp
# repo: https://www.nerdfonts.com

# --- Start of the script code ---
# architectures: x86_64, aarch64
# requires-script-api: 1

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
_release_base_url="https://github.com/ryanoasis/nerd-fonts/releases/latest/download"
_fonts_dir="$HOME/.local/share/fonts"
_archive_dir="$(mktemp -d "$PWD/nerdfonts.XXXXXX")" || fatal "Cannot stage fonts"
trap 'rm -rf -- "$_archive_dir"' EXIT
_work_dir="${_archive_dir}/work"

declare -A _font_urls=(
	["JetBrainsMono"]="${_release_base_url}/JetBrainsMono.tar.xz"
	["FiraCode"]="${_release_base_url}/FiraCode.tar.xz"
	["Hack"]="${_release_base_url}/Hack.tar.xz"
	["Meslo"]="${_release_base_url}/Meslo.tar.xz"
	["AdwaitaMono"]="${_release_base_url}/AdwaitaMono.tar.xz"
)

_font_names=(JetBrainsMono FiraCode Hack Meslo AdwaitaMono)
if _selected_fonts_text=$(listselect --title "Choose Nerd Fonts" --all "${_font_names[@]}"); then
	mapfile -t _selected_fonts <<< "${_selected_fonts_text}"
else
	zenwrn "No font selected"
	exit 0
fi

[ ${#_selected_fonts[@]} -gt 0 ] || { zenwrn "No font selected"; exit 0; }

mkdir -p "${_work_dir}"

for _font in "${_selected_fonts[@]}"; do
	_font_url="${_font_urls[${_font}]}"
	[ -n "${_font_url}" ] || fatal "Unknown Nerd Font selected: ${_font}"

	_archive="${_archive_dir}/${_font}.tar.xz"
	_extract_dir="${_work_dir}/${_font}"

	mkdir -p "${_extract_dir}" || fatal "Failed to prepare ${_font} extraction directory"

	font_download "${_font_url}" "${_archive}"
	tar -xJf "${_archive}" -C "${_extract_dir}" || fatal "Failed to extract ${_font}"

	find "${_extract_dir}" -type f \( -name "*.ttf" -o -name "*.otf" \) | grep -q . || fatal "No font files found for ${_font}"

done

# Every extracted file passes the data-kind architecture preflight again inside font_install.
for _font in "${_selected_fonts[@]}"; do
    mapfile -d '' -t _files < <(find "${_work_dir}/${_font}" -type f \( -name '*.ttf' -o -name '*.otf' \) -print0)
    font_install "$_font" "${_files[@]}"
done

fc-cache -f "${_fonts_dir}" && {
	zeninf "$msg018"
} || {
	fatal "Nerd Fonts installation unsuccessful"
}
