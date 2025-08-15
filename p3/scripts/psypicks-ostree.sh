#!/bin/bash
# name: pdefaults
# description: pdefaults_desc
# icon: pdefaults.png
# compat: ostree
# reboot: ostree

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../libs/helpers.lib"
# functions
get_heroic () {
    local tag=$(curl -s https://api.github.com/repos/Heroic-Games-Launcher/HeroicGamesLauncher/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    local ver="${tag#v}"
    if ! rpm -qi "heroic" 2>/dev/null; then
        wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
        sudo rpm-ostree install "Heroic-${ver}-linux-x86_64.rpm" || { echo "Heroic installation failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
        rm "Heroic-${ver}-linux-x86_64.rpm"
    else
        # update if already installed
        local hostver=$(rpm -qi "heroic" 2>/dev/null | grep "^Version" | awk '{print $3}')
        if [[ "$hostver" != "$ver" ]]; then
            wget "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/${tag}/Heroic-${ver}-linux-x86_64.rpm"
            sudo rpm-ostree remove heroic
            sudo rpm-ostree install "Heroic-${ver}-linux-x86_64.rpm" || { echo "Heroic update failed"; rm -f "Heroic-${ver}-linux-x86_64.rpm"; return 1; }
            rm "Heroic-${ver}-linux-x86_64.rpm"
        else
            zenity --info --text "$msg281" --height=300 --width=300
        fi
    fi
}
# obs pipewire audio capture plugin installation
obs_pipe () {
    if [ ! -d "$HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio" ]; then
        local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
        mkdir obspipe
        cd obspipe
        wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
        tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
        mkdir -p $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio
        cp -rf linux-pipewire-audio/* $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio/
        sudo flatpak override --filesystem=xdg-run/pipewire-0 com.obsproject.Studio
        cd ..
        rm -rf obspipe
    else
        local ver=$(curl -s "https://api.github.com/repos/dimtpap/obs-pipewire-audio-capture/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
        mkdir obspipe
        cd obspipe
        wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/download/${ver}/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
        tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
        mkdir -p $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio
        cp -rf linux-pipewire-audio/* $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/linux-pipewire-audio/
        cd ..
        rm -rf obspipe
    fi
}
if command -v flatpak &> /dev/null && command -v rpm-ostree &> /dev/null; then
    cd $HOME
    mkdir psypicks || exit 1
    cd psypicks || exit 1
    sudo_rq
    rpmfusion_chk
    packages=(steam steam-devices lutris vlc)
    if [[ "$XDG_CURRENT_DESKTOP" == *"GNOME"* ]]; then
        packages+=(gnome-tweaks)
    fi
    _install_
    get_heroic
    flatpaks=(org.prismlauncher.PrismLauncher io.missioncenter.MissionCenter com.github.tchx84.Flatseal com.vysp3r.ProtonPlus com.dec05eba.gpu_screen_recorder com.github.Matoking.protontricks com.obsproject.Studio com.discordapp.Discord)
    if [[ "$XDG_CURRENT_DESKTOP" == *"GNOME"* ]]; then
        flatpaks+=(com.mattjakeman.ExtensionManager)
    fi
    _flatpak_
    obs_pipe
    zenity --info --text "$msg036" --height=300 --width=300
else
    fatal "$msg077"
fi