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

if _zenity_can_run; then
	if mapfile -t _selected_ver < <(zenity --list \
		--title=".NET SDK" \
		--width=420 --height=320 \
		--column="Selected" --column="Version" --column="Link" \
		--hide-column=3 \
		--print-column=2 \
		--separator=$'\n' \
		--checklist --multiple \
		FALSE "10" "https://dotnet.microsoft.com/download/dotnet/10.0" \
		FALSE "9" "https://dotnet.microsoft.com/download/dotnet/9.0" \
		FALSE "8" "https://dotnet.microsoft.com/download/dotnet/8.0"); then
		: # User selected versions
	else
		zenwrn "No version selected"
		exit 0
	fi
else
    _selected_ver=(10 9 8)
fi

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