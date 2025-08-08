#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
sboost_run=""
dsplitm_run=""
# supermenu checklist
gsupermenu () {

    local selection
    local selection_str
    local selected
    local search_item
    local item
    declare -a search_item=(
        "Steam"
        "Lutris"
        "Heroic Games Launcher"
        "ProtonPlus"
        "SteamTinkerLaunch"
        "NexusMods"
        "Sober"
        "Osu!"
        "Prism Launcher"
        "Bedrock Launcher"
        "Discord"
        "Gamemode"
        "Gamescope"
        "Mangohud"
        "GOverlay"
        "GeForce NOW"
        "Shader Booster"
        "Disable SLM"
        "Oversteer"
        "WiVRn"
        "Wine"
        "Runners"
        "NexusMods"
    )

    while true; do

        selection_str=$(zenity --list --checklist --title="Gaming Menu" \
            --column="" \
            --column="Apps" \
            FALSE "Steam" \
            FALSE "Lutris" \
            FALSE "Heroic Games Launcher" \
            FALSE "ProtonPlus" \
            FALSE "SteamTinkerLaunch" \
            FALSE "NexusMods" \
            FALSE "Sober" \
            FALSE "Osu!" \
            FALSE "Bedrock Launcher" \
            FALSE "Discord" \
            FALSE "Gamemode" \
            FALSE "Gamescope" \
            FALSE "Mangohud" \
            FALSE "GOverlay" \
            FALSE "GeForce NOW" \
            FALSE "Shader Booster" \
            FALSE "Disable SLM" \
            FALSE "Oversteer" \
            FALSE "WiVRn" \
            FALSE "Wine - Custom Runners" \
            --height=830 --width=330 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra selection <<< "$selection_str"

        for item in "${search_item[@]}"; do
            for selected in "${selection[@]}"; do
                if [[ "$selected" == "$item" ]]; then
                    case $item in
                        "Steam") _steam="steam" ;;
                        "Lutris") _lutris="net.lutris.Lutris" ;;
                        "Heroic Games Launcher") _heroic="com.heroicgameslauncher.hgl" ;;
                        "ProtonPlus") _pp="com.vysp3r.ProtonPlus" ;;
                        "SteamTinkerLaunch") _stl="com.valvesoftware.Steam.Utility.steamtinkerlaunch" ;;
                        "NexusMods") _nexmod="yes" ;;
                        "Sober") _sobst="org.vinegarhq.Sober" ;;
                        "Osu!") _osuf="sh.ppy.osu" ;;
                        "Bedrock Launcher") _mcbe="io.mrarm.mcpelauncher" ;;
                        "Discord") _disc="com.discordapp.Discord" ;;
                        "Gamemode") _gmode="gamemode" ;;
                        "Gamescope") _gscope="gamescope" ;;
                        "Mangohud") _mhud="mangohud" ;;
                        "GOverlay") _govl="goverlay" ;;
                        "GeForce NOW") _gfn="yes" ;;
                        "Shader Booster") _sboost="yes" ;;
                        "Disable SLM") _dsplitm="yes" ;;
                        "Oversteer") _steer="io.github.berarma.Oversteer" ;;
                        "WiVRn") _wivrn="io.github.wivrn.wivrn" ;;
                        "Wine - Custom Runners") _runner="runners" ;;
                    esac
                fi
            done
        done

        install_flatpak
        install_native
        if [ ! -f /.autopatch.state ]; then
            if [[ -n "$_sboost" ]]; then
                sboost_lib
            fi
            if [[ -n "$_dsplitm" ]]; then
                dsplitm_lib
            fi
        fi
        runners_t
        nexusmods_t
        if [[ -n "$flatpak_run" || -n "$dsplitm_run" || -n "$sboost_run" ]]; then
            zeninf "$msg036"
        else
            zeninf "$msg018"
        fi
        break

    done

}

# installer functions
# native packages
install_native () {

    local codename=$(lsb_release -sc 2>/dev/null || grep VERSION_CODENAME /etc/os-release | cut -d= -f2)
    local _packages=($_steam $_gmode $_govl $_gscope $_mhud)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            if [[ -n "$_steam" ]]; then
                cd $HOME
                wget https://cdn.fastly.steamstatic.com/client/installer/steam.deb
                sudo apt install ./steam.deb
                rm steam.deb
            fi
        fi
        if [[ -n "$_gscope" ]]; then
            if command -v flatpak &> /dev/null; then
                flatpak install --or-update --system -y org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/24.08
            fi
            if [ "$ID" == "debian" ] && [[ "$codename" =~ ^(trixie|testing)$ ]]; then
                cd $HOME
                wget http://ftp.us.debian.org/debian/pool/contrib/g/gamescope/gamescope_3.16.14-1_amd64.deb
                sudo apt install ./gamescope_3.16.14-1_amd64.deb
                rm gamescope_3.16.14-1_amd64.deb
            fi
        fi
        if [[ -n "$_mhud" ]]; then
            if command -v flatpak &> /dev/null; then
                flatpak install --or-update --system -y com.valvesoftware.Steam.VulkanLayer.MangoHud/x86_64/stable org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08
            fi
        fi
    fi
    _install_

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_lutris $_heroic $_pp $_stl $_sobst $_disc $_wivrn $_steer $_mcbe $_osuf)
    if [[ -n "$_flatpaks" ]] || [[ -n "$_steam" ]] || [[ -n "$_gfn" ]]; then
        if command -v flatpak &> /dev/null; then
            flatpak_in_lib
            _flatpak_
            if [[ -n "$_steam" ]]; then
                flatpak install --or-update -u -y com.valvesoftware.Steam
                sleep 1
                sed -i 's/^Name=Steam$/Name=Steam (Flatpak)/' "$HOME/.local/share/applications/com.valvesoftware.Steam.desktop"
            fi
            if [[ -n "$_gfn" ]]; then
                flatpak remote-add --user --if-not-exists GeForceNOW
                flatpak install -y --user GeForceNOW com.nvidia.geforcenow
            fi
            if [[ -n "$_steer" ]]; then
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
                zeninf "$msg146"
                xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices
            fi
            if [[ -n "$_mcbe" ]]; then
                zeninf "$msg161"
            fi
        else
            if zenity --question --text "$msg085" --width 360 --height 300; then
                flatpak_run="1"
                flatpak_in_lib
                _flatpak_
                if [[ -n "$_steam" ]]; then
                    flatpak install --or-update -u -y com.valvesoftware.Steam
                    sed -i 's/^Name=Steam$/Name=Steam (Flatpak)/' "$HOME/.local/share/applications/com.valvesoftware.Steam.desktop"
                fi
                if [[ -n "$_gfn" ]]; then
                    flatpak remote-add --user --if-not-exists GeForceNOW
                    flatpak install -y --user GeForceNOW com.nvidia.geforcenow
                fi
                if [[ -n "$_steer" ]]; then
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
                    zeninf "$msg146"
                    xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices
                fi
                if [[ -n "$_mcbe" ]]; then
                    zeninf "$msg161"
                fi
            else
                nonfatal "$msg132"
            fi
        fi
    fi

}

# custom runners
runners_t () {

    if [[ -n "$_runner" ]]; then
        local subscript="$_runner"
        _invoke_
    fi

}

nexusmods_t () {

    if [[ -n "$_nexmod" ]]; then
        local ver=$(curl -s "https://api.github.com/repos/Nexus-Mods/NexusMods.App/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
        cd $HOME
        insta fuse3
        wget https://github.com/Nexus-Mods/NexusMods.App/releases/download/${ver}/NexusMods.App.x86_64.AppImage
        ./NexusMods.App.x86_64.AppImage --appimage-extract
        cd squashfs-root
        mkdir -p nexusmods
        if [ -d /usr/bin/nexusmods ]; then
            cp -rf usr/bin/ nexusmods
            sudo rm -rf /usr/bin/nexusmods
            sudo cp -r nexusmods /usr/bin
        else
            cp -rf usr/bin/ nexusmods
            sudo cp -r nexusmods /usr/bin
            sudo cp -r usr/share/applications/ /usr/share/applications/
            sudo cp -r usr/share/icons/hicolor/scalable/apps/ /usr/share/icons/hicolor/scalable/apps/
            sudo cp -r usr/share/metainfo/ /usr/share/metainfo/
            sudo sed -i 's|^Exec=/usr/bin/NexusMods.App %u$|Exec=/usr/bin/nexusmods/NexusMods.App %u|' "/usr/share/applications/com.nexusmods.app.desktop"
        fi
        cd ..
        sleep 1
        rm -rf squashfs-root
        rm NexusMods.App.x86_64.AppImage
    fi

}

# runtime
. /etc/os-release
source /usr/bin/linuxtoys/linuxtoys.lib
_lang_
source /usr/bin/linuxtoys/${langfile}
gsupermenu
