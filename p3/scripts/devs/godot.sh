#!/bin/bash
# name: Godot Engine 4
# version: 1.0
# description: godot_desc
# icon: godot.svg
# repo: https://godotengine.org

# --- Start of the script code ---
# when there are updates, make sure to edit the .desktop files in resources/godot as well!
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
cd $HOME
get_latest_godot_url() {
    curl -s https://api.github.com/repos/godotengine/godot/releases/latest | \
    grep browser_download_url | grep 'stable_linux.x86_64.zip' | head -n 1 | cut -d '"' -f 4
}
GODOT_URL=$(get_latest_godot_url)
GODOT_ZIP="Godot_latest_linux.x86_64.zip"
# first install
if [ ! -d "$HOME/.local/godot" ]; then
    wget "$GODOT_URL" -O "$GODOT_ZIP"
    unzip "$GODOT_ZIP"
    GODOT_BIN=$(ls Godot*_linux.x86_64)
    mv "$GODOT_BIN" Godot
    mkdir -p "$HOME/.local/godot"
    cp Godot -f "$HOME/.local/godot"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
    cp godot.png "$HOME/.local/godot"
    rm Godot
    rm godot.png
    rm "$GODOT_ZIP"
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.desktop
    cp godot.desktop "$HOME/.local/share/applications/"
    rm godot.desktop
else # update
    wget "$GODOT_URL" -O "$GODOT_ZIP"
    unzip "$GODOT_ZIP"
    GODOT_BIN=$(ls Godot*_linux.x86_64)
    mv "$GODOT_BIN" Godot
    cp Godot -f "$HOME/.local/godot"
    rm Godot
    rm "$GODOT_ZIP"
fi
zeninf "$msg018"