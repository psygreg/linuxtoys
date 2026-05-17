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
_cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/linuxtoys"
_cache_file="${_cache_dir}/nerdfonts-assets.txt"
_cache_ttl_sec=$((6 * 60 * 60))

declare -A _font_latest_url
_all_asset_urls=()

_refresh_cache=true
if [ -s "${_cache_file}" ]; then
	_now=$(date +%s)
	_mtime=$(date -r "${_cache_file}" +%s 2>/dev/null || printf '0')
	_age=$((_now - _mtime))
	[ "${_age}" -lt "${_cache_ttl_sec}" ] && _refresh_cache=false
fi

if ! ${_refresh_cache}; then
	mapfile -t _all_asset_urls < "${_cache_file}"
fi

if ${_refresh_cache}; then
	mkdir -p "${_cache_dir}"
	_cache_tmp="${_cache_file}.tmp"
	: > "${_cache_tmp}"

	_page=1
	while :; do
		_response=$(curl -sSL \
			-H "Accept: application/vnd.github+json" \
			-H "User-Agent: linuxtoys-nerdfonts-installer" \
			-w '\n%{http_code}' \
			"https://api.github.com/repos/${_gh_user}/${_gh_repo}/releases?per_page=100&page=${_page}") || {
			rm -f "${_cache_tmp}"
			fatal "Could not fetch Nerd Fonts release metadata"
		}

		_http_code=${_response##*$'\n'}
		_page_json=${_response%$'\n'*}

		if [ "${_http_code}" = "403" ] && printf '%s' "${_page_json}" | grep -qi 'rate limit'; then
			rm -f "${_cache_tmp}"
			fatal "GitHub API rate limit reached. Please try again later."
		fi

		if [ "${_http_code}" -ge 400 ] 2>/dev/null; then
			rm -f "${_cache_tmp}"
			fatal "GitHub API request failed (HTTP ${_http_code})"
		fi

		[ "${_page_json}" = "[]" ] && break

		mapfile -t _page_assets < <(
			printf '%s' "${_page_json}" | grep -Po '"browser_download_url":\s*"\K[^"]+\.tar\.xz'
		)

		if [ ${#_page_assets[@]} -gt 0 ]; then
			_all_asset_urls+=("${_page_assets[@]}")
			printf '%s\n' "${_page_assets[@]}" >> "${_cache_tmp}"
		fi

		_page=$((_page + 1))
	done

	mv -f "${_cache_tmp}" "${_cache_file}"
fi

for _asset_url in "${_all_asset_urls[@]}"; do
	_asset_file=${_asset_url##*/}
	_font_name=${_asset_file%%.*}

	# Releases are returned newest-first, so first hit per font is the latest available release for that font.
	[ -z "${_font_latest_url[${_font_name}]}" ] && _font_latest_url["${_font_name}"]="${_asset_url}"
done

[ ${#_font_latest_url[@]} -eq 0 ] && fatal "Could not find Nerd Fonts assets"

_fonts_names=()
mapfile -t _fonts < <(printf '%s\n' "${!_font_latest_url[@]}" | sort -f)
for _font in "${_fonts[@]}"; do
	_fonts_names+=(FALSE "${_font_latest_url[${_font}]}" "${_font}")
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
			curl -fsSL "${_font_url}" -o- | tar -xJf - -C "${_font_path}"
		done
		fc-cache -fv;
	) && { zeninf "$msg018"; } || { fatal "Nerd-Fonts installation unsuccessful"; }
} || {
	zenwrn "No font selected"
}
