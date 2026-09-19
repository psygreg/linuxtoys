#!/bin/bash
# name: Godot Engine 4 Sharp
# version: 1.0
# description: godotsharp_desc
# icon: godotsh.svg
# compat: fedora, ubuntu, debian, ostree, ublue, suse, arch, cachy, rhel
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
    extract_dir="$(mktemp -d)"
    unzip -q "$GODOT_MONO_ZIP" -d "$extract_dir"
    godot_root=$(find "$extract_dir" -mindepth 1 -maxdepth 1 -type d -print -quit)
    [ -n "$godot_root" ] || die "Could not find extracted Godot directory."
    cp -a "$godot_root"/. "$HOME/.local/godot/"
    rm -rf "$extract_dir"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/godot/godot.png
    copy_ godot.png "$HOME/.local/godot"
    
    godot_binary=$(find "$HOME/.local/godot" -maxdepth 1 -type f -name 'Godot_v*-stable_mono_linux.x86_64' -print -quit)
    [ -n "$godot_binary" ] || die "Could not find the extracted Godot executable."
    chmod +x "$godot_binary"
    ln -sfn "$godot_binary" "$HOME/.local/godot/godot-mono"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/godot/godotsharp.desktop
    prep_create "$HOME/.local/share/applications/godotsharp.desktop"
    copy_ godotsharp.desktop "$HOME/.local/share/applications"
    sed -i "s|\$HOME|$HOME|g" "$HOME/.local/share/applications/godotsharp.desktop"
    call_script dotnet
else # update
    wget "$GODOT_MONO_URL" -O "$GODOT_MONO_ZIP"
    prep_dir_edit "$HOME/.local/godot"
    unzip -d "$HOME/.local/godot" "$GODOT_MONO_ZIP"
fi
zeninf "$msg018"