#!/bin/bash
# name: JetBrains Toolbox
# version: 1.0
# description: jbtb_desc
# icon: toolbox.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
cd $HOME
wget https://download-cdn.jetbrains.com/toolbox/jetbrains-toolbox-2.6.2.41321.tar.gz
# first installation
if [ ! -d "$HOME/.local/toolbox" ]; then
    if zenity --question --text "$msg174" --width 360 --height 300; then
        _packages=(fuse3)
        sudo_rq
        _install_
        tar -xvzf jetbrains-toolbox-2.6.2.41321.tar.gz
        sleep 1
        mv $(find . -maxdepth 1 -type d -name "jetbrains-*") toolbox
        sleep 1
        ./toolbox/jetbrains-toolbox --appimage-extract
        rm -r toolbox
        mv squashfs-root toolbox
        cp -rf toolbox $HOME/.local
        rm jetbrains-toolbox-2.6.2.41321.tar.gz
        rm -rf toolbox
        # Create applications directory if it doesn't exist
        mkdir -p "$HOME/.local/share/applications"
        # Download and install desktop shortcut
        cd "$HOME" || return
        if wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/jetbrains-toolbox.desktop; then
            if cp -f jetbrains-toolbox.desktop "$HOME/.local/share/applications/"; then
                rm jetbrains-toolbox.desktop
            else
                fatal "Failed to copy desktop shortcut to applications directory"
            fi
        else
            fatal "Failed to download desktop shortcut file"
        fi
        if grep -q "alias jbtoolbox=" ~/.bashrc; then
            return
        else
            echo "alias jbtoolbox=\"$HOME/.local/toolbox/jetbrains-toolbox\"" >> ~/.bashrc
            source ~/.bashrc
        fi
        zeninf "$msg018"
    else
        zeninf "$msg175"
        exit 1
    fi
else # update or repair
    tar -xvzf jetbrains-toolbox-2.6.2.41321.tar.gz
    sleep 1
    mv $(find . -maxdepth 1 -type d -name "jetbrains-*") toolbox
    sleep 1
    ./toolbox/jetbrains-toolbox --appimage-extract
    rm -r toolbox
    mv squashfs-root toolbox
    cp -rf toolbox $HOME/.local
    rm jetbrains-toolbox-2.6.2.41321.tar.gz
    rm -rf toolbox
    # Create applications directory if it doesn't exist
    mkdir -p "$HOME/.local/share/applications"
    # Download and install desktop shortcut (in case it's missing or needs update)
    cd "$HOME" || return
    if wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/jetbrains-toolbox.desktop; then
        if cp -f jetbrains-toolbox.desktop "$HOME/.local/share/applications/"; then
            rm jetbrains-toolbox.desktop
        else
            fatal "Failed to copy desktop shortcut to applications directory"
        fi
    else
        fatal "Failed to download desktop shortcut file"
    fi
    zeninf "$msg018"
fi