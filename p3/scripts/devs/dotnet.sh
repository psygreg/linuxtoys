#!/bin/bash
# name: .NET SDK
# version: 1.0
# description: dotnet_desc
# icon: dotnet.svg
# compat: fedora, ostree, debian, ubuntu, ublue, rhel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp
sudo_rq

_selected_ver_text=$(listselect --title ".NET SDK" "10" "9" "8") || {
	zenwrn "No version selected"
	exit 100
}
mapfile -t _selected_ver <<< "$_selected_ver_text"

if is_debian; then
    wget https://packages.microsoft.com/config/debian/13/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
    sudo dpkg -i packages-microsoft-prod.deb
    rm packages-microsoft-prod.deb
    sudo apt update
fi

for version in "${_selected_ver[@]}"; do
    if [ "$version" = "9" ] && is_ubuntu; then
        sudo add-apt-repository ppa:dotnet/backports
        sudo apt update
    fi
    case "$version" in
        "8") pkg_install dotnet-sdk-8.0 ;;
        "9") pkg_install dotnet-sdk-9.0 ;;
        "10") pkg_install dotnet-sdk-10.0 ;;
    esac
done
zeninf "$finishmsg"