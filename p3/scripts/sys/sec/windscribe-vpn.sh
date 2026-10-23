#!/bin/bash
# name: Windscribe VPN
# version: 1.0
# description: Windscribe VPN
# icon: windscribe.svg
# repo: https://windscribe.com
# compat: !solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp

# Windscribe's old one-shot install endpoints (windscribe.com/install/desktop/*)
# now return an HTML landing page, so packages are resolved from the official
# GitHub releases (Windscribe/Desktop-App) instead. Asset names carry the version
# (windscribe_<ver>_amd64[_fedora|_opensuse].deb|rpm|pkg.tar.zst), so the download
# URL is matched from the release rather than reconstructed from a version string.
REPO="Windscribe/Desktop-App"
GITHUB_API="https://api.github.com/repos/${REPO}/releases/latest"

resolve_asset () { # echoes the download URL for the requested asset pattern
    local pattern="$1"
    local json url
    json=$(curl -fsSL -H "Accept: application/vnd.github+json" "$GITHUB_API") \
        || { fatal "Failed to query the latest Windscribe release."; exit 1; }
    url=$(echo "$json" \
        | grep -oP '"browser_download_url":\s*"\K[^"]+' \
        | grep -E "$pattern" | head -n 1)
    [ -n "$url" ] || { fatal "It was not possible to find the Windscribe package for your system."; exit 1; }
    echo "$url"
}

if is_ubuntu || is_debian; then
	url=$(resolve_asset 'windscribe_[0-9][^"]*_amd64\.deb$')
	curl -fL "$url" -o windscribe.deb || fatal "Failed to download Windscribe."
	pkg_fromfile windscribe.deb
	sudo apt-get install -f -y
elif is_fedora || is_ostree || is_rhel; then
	url=$(resolve_asset 'windscribe_[0-9][^"]*_amd64_fedora\.rpm$')
	curl -fL "$url" -o windscribe.rpm || fatal "Failed to download Windscribe."
	pkg_fromfile windscribe.rpm
elif is_arch || is_cachy; then
	url=$(resolve_asset 'windscribe_[0-9][^"]*_amd64\.pkg\.tar\.zst$')
	curl -fL "$url" -o windscribe.pkg.tar.zst || fatal "Failed to download Windscribe."
	pkg_fromfile windscribe.pkg.tar.zst
elif is_suse; then
	url=$(resolve_asset 'windscribe_[0-9][^"]*_amd64_opensuse\.rpm$')
	curl -fL "$url" -o windscribe.rpm || fatal "Failed to download Windscribe."
	pkg_fromfile windscribe.rpm
else
    fatal "$msg077"
fi
zeninf "$msg018"
