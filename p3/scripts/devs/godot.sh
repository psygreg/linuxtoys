#!/bin/bash
# name: Godot Engine 4
# version: 1.0
# description: godot_desc
# icon: godot.svg
# repo: https://godotengine.org

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp
get_latest_godot_url() {
    curl -s https://api.github.com/repos/godotengine/godot/releases/latest | \
    grep browser_download_url | grep 'stable_linux.x86_64.zip' | head -n 1 | cut -d '"' -f 4
}
GODOT_URL=$(get_latest_godot_url)
GODOT_ZIP="Godot_latest_linux.x86_64.zip"
# first install
if [ ! -d "$HOME/.local/godot" ]; then
    prep_dir "$HOME/.local/godot"
    wget "$GODOT_URL" -O "$GODOT_ZIP"
    unzip "$GODOT_ZIP"
    GODOT_BIN=$(ls Godot*_linux.x86_64)
    move_ "$GODOT_BIN" Godot
    mkdir -p "$HOME/.local/godot"
    copy_ Godot -f "$HOME/.local/godot"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
    copy_ godot.png -f "$HOME/.local/godot"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.desktop
    copy_ godot.desktop -f "$HOME/.local/share/applications/"
else # update
    wget "$GODOT_URL" -O "$GODOT_ZIP"
    unzip "$GODOT_ZIP"
    GODOT_BIN=$(ls Godot*_linux.x86_64)
    prep_edit "$HOME/.local/godot/Godot"
    move_ "$GODOT_BIN" Godot
    copy_ Godot -f "$HOME/.local/godot"
fi
zeninf "$msg018"