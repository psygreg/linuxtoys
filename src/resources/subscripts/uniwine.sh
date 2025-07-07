#!/bin/bash

# set up latest proton-cachyos
getproton () {

    # set default wineprefix
    local DEST_FILE=""
    cd $HOME
    if [ ! -d ${HOME}/wineapps ]; then
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/wine/wineprefix.cat
        if [[ -f "${HOME}/.bash_profile" ]]; then
            DEST_FILE="${HOME}/.bash_profile"
        elif [[ -f "$HOME/.profile" ]]; then
            DEST_FILE="${HOME}/.profile"
        elif [[ -f "$HOME/.zshrc" ]]; then
            DEST_FILE="${HOME}/.zshrc"
        fi
        cp $DEST_FILE ${DEST_FILE}.bak
        while IFS= read -r line; do
            grep -Fxq "$line" "$DEST_FILE" || echo "$line" >> "$DEST_FILE"
        done < wineprefix.cat
        rm wineprefix.cat
    fi
    # download and install proton
    local tag=$(curl -s "https://api.github.com/repos/CachyOS/proton-cachyos/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    wget https://github.com/CachyOS/proton-cachyos/releases/download/${tag}/proton-${tag}-x86_64.tar.xz
    tar -xf proton-${tag}-x86_64.tar.xz
    sleep 1
    mv proton-${tag}-x86_64 proton-cachyos
    sleep 1
    if [ ! -d $HOME/wineapps ]; then
        mkdir -p $HOME/wineapps
        cd proton-cachyos/files
        sudo cp -r bin/* /usr/bin
        sudo cp -r share/* /usr/share
        sudo cp -r lib/* /usr/lib
        cd ..
        cd protonfixes/files
        sudo cp -r bin/* /usr/bin
        sudo cp -r lib/* /usr/lib
    else
        cd proton-cachyos/files
        sudo cp -rf bin/* /usr/bin
        sudo cp -rf share/* /usr/share
        sudo cp -rf lib/* /usr/lib
        cd ..
        cd protonfixes/files
        sudo cp -f bin/winetricks /usr/bin
        sudo cp -rf lib/* /usr/lib
    fi
    cd $HOME
    rm -rf proton-cachyos
    rm proton-${tag}-x86_64.tar.xz
    # set aliases and app menu shortcut
    cp .bashrc .bashrc.bak
    grep -qxF 'alias wine="/usr/bin/wine64"' ~/.bashrc || echo 'alias wine="/usr/bin/wine64"' >> ~/.bashrc
    grep -qxF 'alias winetricks="/usr/bin/winetricks"' ~/.bashrc || echo 'alias winetricks="/usr/bin/winetricks"' >> ~/.bashrc
    source ~/.bashrc
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/wine/wine.desktop
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/wine/wine-lt.png
    sudo cp wine.desktop /usr/share/applications/
    sudo cp wine-lt.png /usr/share/icons/hicolor/scalable/apps/
    rm wine.desktop
    rm wine-lt.png

}

# prepare necessary winetricks
winetrix () {

    local title="UniWine"
    local msg="$msg236"
    _msgbox_
    echo "Setting up wineprefix"
    sleep 2
    wine winecfg
    winetricks -q win11
    local msg="$msg237"
    _msgbox_
    # install necessary winetricks
    winetricks vcrun2008 vcrun2010 vcrun2012 vcrun2013 vcrun2022 d3dcompiler_42 d3dcompiler_43 d3dcompiler_46 d3dcompiler_47 d3drm d3dx10 d3dx11_42 d3dx11_43 d3dx9 d3dxof dotnet9 dotnetdesktop9 dxvk pdh vkd3d vcrun6 xinput andale arial comicsans courier georgia impact times trebuchet verdana webdings corefonts cmd ucrtbase2019 tahoma
    # check nvidia
    local GPU=$(lspci | grep -iE 'vga|3d' | grep -i nvidia)
    if [[ -n "$GPU" ]]; then
        winetricks dxvk_nvapi
    fi
    # check wayland session
    if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        winetricks graphics=wayland
    fi

}

# uninstaller
uniwinerm () {

    # remove files
    sudo rm /usr/bin/msidb
    sudo rm /usr/bin/wine
    sudo rm /usr/bin/wine-preloader
    sudo rm /usr/bin/wine64
    sudo rm /usr/bin/wine64-preloader
    sudo rm /usr/bin/wineserver
    sudo rm /usr/bin/winetricks
    sudo rm -rf /usr/share/wine
    sudo rm -rf /usr/share/xalia
    sudo rm /usr/share/applications/wine.desktop
    sudo rm /usr/share/icons/hicolor/scalable/apps/wine-lt.png
    # restore old profile and bashrc
    local DEST_FILE=""
    if [[ -f "${HOME}/.bash_profile" ]]; then
        DEST_FILE="${HOME}/.bash_profile"
    elif [[ -f "$HOME/.profile" ]]; then
        DEST_FILE="${HOME}/.profile"
    elif [[ -f "$HOME/.zshrc" ]]; then
        DEST_FILE="${HOME}/.zshrc"
    fi
    mv -f ${DEST_FILE}.bak $DEST_FILE
    mv -f ~/.bashrc.bak ~/.bashrc

}

# runtime
# source lib and language
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# check if wine is already installed
if command -v wine >/dev/null 2>&1; then
    title="UniWine"
    msg="$msg238"
    _msgbox_
fi
# menu
while :; do

    CHOICE=$(whiptail --title "UniWine" --menu "" 25 78 16 \
        "0" "$msg239" \
        "1" "$msg240" \
        "2" "$msg070" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) getproton && winetrix && break;;
    1) uniwinerm && break;;
    2 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
