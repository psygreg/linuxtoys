#!/bin/bash
# name: Godot Engine 4 Sharp
# version: 1.0
# description: godotsharp_desc
# icon: godotsh.svg
# compat: fedora, ubuntu, debian, ostree, ublue, suse, arch, cachy
# repo: https://godotengine.org

# --- Start of the script code ---
# when there are updates, make sure to edit the .desktop files in resources/godot as well!
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp
get_latest_godot_mono_url() {
    curl -s https://api.github.com/repos/godotengine/godot/releases/latest | \
    grep browser_download_url | grep 'stable_mono_linux_x86_64.zip' | head -n 1 | cut -d '"' -f 4
}
GODOT_MONO_URL=$(get_latest_godot_mono_url)
GODOT_MONO_ZIP="Godot_latest_mono_linux.x86_64.zip"

# first install
if [ ! -d "$HOME/.local/godot" ]; then
    wget "$GODOT_MONO_URL" -O "$GODOT_MONO_ZIP"
    prep_dir "$HOME/.local/godot"
    unzip -d "$HOME/.local/godot" "$GODOT_MONO_ZIP"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
    copy_ godot.png "$HOME/.local/godot"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godotsharp.desktop
    prep_create "$HOME/.local/share/applications/godotsharp.desktop"
    copy_ godotsharp.desktop "$HOME/.local/share/applications"
    sudo_rq
    if is_debian; then
        wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
        sudo dpkg -i packages-microsoft-prod.deb
        sudo apt update
    elif [[ "$NAME" =~ "openSUSE Leap" ]]; then
        sudo zypper in libicu -y
        sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        wget https://packages.microsoft.com/config/opensuse/15/prod.repo
        move_ prod.repo /etc/zypp/repos.d/microsoft-prod.repo
        sudo chown root:root /etc/zypp/repos.d/microsoft-prod.repo
    fi
    if is_arch || is_cachy; then
        pkg_install dotnet-sdk-9.0-bin
    else         
        pkg_install dotnet-sdk-9.0
    fi
else # update
    wget "$GODOT_MONO_URL" -O "$GODOT_MONO_ZIP"
    prep_dir_edit "$HOME/.local/godot"
    unzip -d "$HOME/.local/godot" "$GODOT_MONO_ZIP"
fi
zeninf "$msg018"