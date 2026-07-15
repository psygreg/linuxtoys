#!/bin/bash
# name: MetaTrader 5
# description: mt5_desc
# icon: mt5.png
# repo: https://www.metatrader5.com
# nocontainer
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

if ! command -v distrobox &>/dev/null; then
    call_script distroshelf
fi

if distrobox create --name metatrader5 --image docker.io/library/ubuntu:24.04; then
    distrobox_created metatrader5
    prep_tmp_noram
    wget https://download.terminal.free/cdn/web/metaquotes.software.corp/mt5/mt5linux.sh
    chmod +x mt5linux.sh
    distrobox enter metatrader5 -- sudo apt update
    distrobox enter metatrader5 -- sudo apt upgrade
    distrobox enter metatrader5 -- ./mt5linux.sh
    _append_transmap "created $HOME/.mt5"
    copy_ "$SCRIPT_DIR/app/icons/mt5.png" "$HOME/.mt5/drive_c/Program Files/MetaTrader 5/"
    prep_create "$HOME/.local/share/applications/mt5.desktop"
    cat > ~/.local/share/applications/metatrader5-distrobox.desktop << EOF
[Desktop Entry]
Name=MetaTrader 5 (distrobox)
Comment=MetaTrader 5 Trading Terminal (running in distrobox container)
Exec=$(command -v distrobox-enter) -n metatrader -- bash -c 'WINEPREFIX="$HOME/.mt5" wine "$HOME/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"'
Icon=$HOME/.mt5/drive_c/Program Files/MetaTrader 5/mt5.png
Terminal=false
Type=Application
Categories=Office;Finance;
StartupWMClass=terminal64.exe
EOF
    zeninf "$finishmsg"
else
    fatal "Failed to set up distrobox container."
fi