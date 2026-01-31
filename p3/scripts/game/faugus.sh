#!/bin/bash
# name: Faugus Launcher
# version: 1.0
# description: faugus_desc
# icon: faugus-launcher.png
# repo: https://github.com/Faugus/faugus-launcher

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
if is_debian || is_ubuntu || is_ostree || is_suse; then
    flatpak_in_lib
    flatpak install --user --noninteractive flathub io.github.Faugus.faugus-launcher
    sudo_rq
    # apply overrides for Steam compatibility
    sudo flatpak override io.github.Faugus.faugus-launcher --filesystem=~/.var/app/com.valvesoftware.Steam/.steam/steam/userdata/
    sudo flatpak override com.valvesoftware.Steam --talk-name=org.freedesktop.Flatpak
    sudo flatpak override com.valvesoftware.Steam --filesystem=~/.var/app/io.github.Faugus.faugus-launcher/config/faugus-launcher/
elif is_fedora || is_arch || is_cachy; then
    sudo_rq
    if is_fedora; then
        sudo dnf -y copr enable faugus/faugus-launcher
    fi
    _packages=(faugus-launcher)
    _install_
fi