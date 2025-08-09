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
        "Wine - Custom Runners"
        "$msg248"
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
            FALSE "$msg248" \
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
            --height=850 --width=330 --separator="|")

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
                        "$msg248") _lsfgvk="1" ;;
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
        if [ -n "$_lsfgvk" ]; then
            lsfg_vk_in
        fi
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

# install lsfg-vk
lsfg_vk_in () {

    local tag=$(curl -s "https://api.github.com/repos/PancakeTAS/lsfg-vk/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    local ver="${tag#v}"
    local DLL_FIND="$(find / -name Lossless.dll 2>/dev/null | head -n 1)"
    if [ -z "$DLL_FIND" ]; then
        nonfatal "Lossless.dll not found. Did you install Lossless Scaling?"
        return 1
    fi
    local DLL_ABSOLUTE_PATH=$(dirname "$(realpath "$DLL_FIND")")
    local ESCAPED_DLL_PATH=$(printf '%s\n' "$DLL_ABSOLUTE_PATH" | sed 's/[&/\]/\\&/g')
    if rpm -qi lsfg-vk &> /dev/null || pacman -Qi lsfg-vk 2>/dev/null 1>&2 || dpkg -s lsfg-vk 2>/dev/null 1>&2; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.deb
            sudo apt install -y ./lsfg-vk-${ver}.x86_64.deb
            rm lsfg-vk-${ver}.x86_64.deb
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            sudo dnf install -y ./lsfg-vk-${ver}.x86_64.rpm
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID_LIKE" == *suse* ]] || [ "$ID" == "suse" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            sudo zypper install -y ./lsfg-vk-${ver}.x86_64.rpm
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.tar.zst
            sudo pacman -U --noconfirm lsfg-vk-${ver}.x86_64.tar.zst
            rm lsfg-vk-${ver}.x86_64.tar.zst
        fi
        if command -v flatpak &> /dev/null; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak 
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            local flatapps=(com.usebottles.bottles net.lutris.Lutris com.valvesoftware.Steam com.heroicgameslauncher.hgl org.prismlauncher.PrismLauncher com.stremio.Stremio at.vintagestory.VintageStory org.vinegarhq.Sober)
            for flatapp in "${flatapps[@]}"; do
                if flatpak info "$flatapp" &> /dev/null; then
                    flatpak override --user --filesystem="$HOME/.config/lsfg-vk:rw" "$flatapp"
                    flatpak override --user --env=LSFG_CONFIG="$HOME/.config/lsfg-vk/conf.toml" "$flatapp"
                    if [ "$flatapp" != "com.valvesoftware.Steam" ]; then
                        flatpak override --user --filesystem="$DLL_ABSOLUTE_PATH:ro" "$flatapp"
                    fi
                fi
            done
        fi
    else
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.deb
            sudo apt install -y ./lsfg-vk-${ver}.x86_64.deb
            rm lsfg-vk-${ver}.x86_64.deb
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            sudo dnf install -y ./lsfg-vk-${ver}.x86_64.rpm
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID_LIKE" == *suse* ]] || [ "$ID" == "suse" ]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.rpm
            sudo zypper install -y ./lsfg-vk-${ver}.x86_64.rpm
            rm lsfg-vk-${ver}.x86_64.rpm
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/lsfg-vk-${ver}.x86_64.tar.zst
            sudo pacman -U --noconfirm lsfg-vk-${ver}.x86_64.tar.zst
            rm lsfg-vk-${ver}.x86_64.tar.zst
        fi
        CONF_LOC="${HOME}/.config/lsfg-vk/conf.toml"
        if [ ! -f "$CONF_LOC" ]; then
            # make sure target dir exists
            mkdir -p ${HOME}/.config/lsfg-vk/
            wget https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/src/patches/conf.toml
            mv conf.toml ${HOME}/.config/lsfg-vk/
        fi
        # register dll location in config file
        sed -i -E "s|^# dll = \".*\"|dll = \"$ESCAPED_DLL_PATH\"|" ${HOME}/.config/lsfg-vk/conf.toml
        # flatpak runtime
        if command -v flatpak &> /dev/null; then
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            wget https://github.com/PancakeTAS/lsfg-vk/releases/download/${tag}/org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak 
            flatpak install --reinstall --user -y ./org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_23.08.flatpak
            rm org.freedesktop.Platform.VulkanLayer.lsfg_vk_24.08.flatpak
            local flatapps=(com.usebottles.bottles net.lutris.Lutris com.valvesoftware.Steam com.heroicgameslauncher.hgl org.prismlauncher.PrismLauncher com.stremio.Stremio at.vintagestory.VintageStory org.vinegarhq.Sober)
            for flatapp in "${flatapps[@]}"; do
                if flatpak info "$flatapp" &> /dev/null; then
                    flatpak override --user --filesystem="$HOME/.config/lsfg-vk:rw" "$flatapp"
                    flatpak override --user --env=LSFG_CONFIG="$HOME/.config/lsfg-vk/conf.toml" "$flatapp"
                    if [ "$flatapp" != "com.valvesoftware.Steam" ]; then
                        flatpak override --user --filesystem="$DLL_ABSOLUTE_PATH:ro" "$flatapp"
                    fi
                fi
            done
        fi
    fi

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
gsupermenu
