#!/bin/bash
# name: Nerd Fonts
# version: 1.0
# description: nerdfonts_desc
# icon: nerdfonts.webp
# repo: https://www.nerdfonts.com

# --- Start of the script code ---
# architectures: x86_64, aarch64
# requires-script-api: 1

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
_release_base_url="https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1"
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

declare -A _font_hashes=(
    [JetBrainsMono]=04d5e8f903693f9dd13e16f867e994834e681eb3c72c0d337a770dcda09010cf
    [FiraCode]=68e3bd6164864b8b514605bc34e3a87ac401c8c48682fcce6478c70263340207
    [Hack]=cdd389472e10e2261520140ff1b382b4f8a226af5fd0b2735b975d31151d9c3c
    [Meslo]=6b6624632dc6873dfb7681c3f818e7c01ab601ab707690b6440933bbe57e2b11
    [AdwaitaMono]=409118887ec166a2342c184ade6734faf5d236a097742cb7085ff42826a1dd94
)
mkdir -p "${_work_dir}"

for _font in "${_selected_fonts[@]}"; do
	_font_url="${_font_urls[${_font}]}"
	[ -n "${_font_url}" ] || fatal "Unknown Nerd Font selected: ${_font}"

	_archive="${_archive_dir}/${_font}.tar.xz"
	_extract_dir="${_work_dir}/${_font}"

	mkdir -p "${_extract_dir}" || fatal "Failed to prepare ${_font} extraction directory"

	font_download "${_font_url}" "${_archive}" "${_font_hashes[${_font}]}"
	tar -xJf "${_archive}" -C "${_extract_dir}" || fatal "Failed to extract ${_font}"

	find "${_extract_dir}" -type f \( -name "*.ttf" -o -name "*.otf" \) | grep -q . || fatal "No font files found for ${_font}"

done

# All selected archives must pass integrity/architecture checks before installation.
for _font in "${_selected_fonts[@]}"; do
    mapfile -d '' -t _files < <(find "${_work_dir}/${_font}" -type f \( -name '*.ttf' -o -name '*.otf' \) -print0)
    font_install "$_font" "${_files[@]}"
done

fc-cache -f "${_fonts_dir}" && {
	zeninf "$msg018"
} || {
	fatal "Nerd Fonts installation unsuccessful"
}
