#!/bin/bash
# name: LeShade
# description: leshade_desc
# icon: leshade.png
# repo: https://github.com/Ishidawg/LeShade

source "$SCRIPT_DIR/libs/linuxtoys.lib"

prep_tmp_noram
# dependencies
pkg_install wine winetricks

download_url=$(curl -fsSL "https://api.github.com/repos/Ishidawg/LeShade/releases/latest" \
	| grep -oP '"browser_download_url": "\K[^" ]*LeShade-x86_64\.AppImage(?=")')
[ -n "$download_url" ] || die "Could not detect the latest LeShade AppImage URL. Please try again later."
wget -O LeShade-x86_64.AppImage "$download_url" || die "Failed to download LeShade AppImage."

pkg_appimage LeShade-x86_64.AppImage
info "$finishmsg"
