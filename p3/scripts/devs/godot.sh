#!/bin/bash
# name: Godot Engine 4
# version: 1.0
# description: godot_desc
# icon: godot

# --- Start of the script code ---
# when there are updates, make sure to edit the .desktop files in resources/godot as well!
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
cd $HOME
# first install
if [ ! -d "$HOME/.local/godot" ]; then
    wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/5c13b07c-aad3-4bde-8712-9f0825758bb2?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T210343Z&X-Amz-Expires=300&X-Amz-Signature=2b5d1d411f853ce8c1eb9045af1b02f3567a4a8de13d754a3f1b3fce345a0051&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_linux.x86_64.zip&response-content-type=application%2Foctet-stream'
    unzip Godot_v4.4.1-stable_linux.x86_64.zip
    mv Godot_v4.4.1-stable_linux.x86_64 Godot
    mkdir -p $HOME/.local/godot
    cp Godot -f $HOME/.local/godot
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
    cp godot.png $HOME/.local/godot
    rm Godot
    rm godot.png
    rm Godot_v4.4.1-stable_linux.x86_64.zip
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.desktop
    cp godot.desktop $HOME/.local/share/applications
    rm godot.desktop
else # update
    wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/5c13b07c-aad3-4bde-8712-9f0825758bb2?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T210343Z&X-Amz-Expires=300&X-Amz-Signature=2b5d1d411f853ce8c1eb9045af1b02f3567a4a8de13d754a3f1b3fce345a0051&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_linux.x86_64.zip&response-content-type=application%2Foctet-stream'
    unzip Godot_v4.4.1-stable_linux.x86_64.zip
    mv Godot_v4.4.1-stable_linux.x86_64 Godot
    cp Godot -f $HOME/.local/godot
    rm Godot
    rm Godot_v4.4.1-stable_linux.x86_64.zip
fi
zeninf "$msg018"