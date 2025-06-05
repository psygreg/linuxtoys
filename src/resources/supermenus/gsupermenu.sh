#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
sboost_run=""
dsplitm_run=""
# supermenu checklist
gsupermenu () {

    local steam_status=$([ "$_steam" = "steam" ] && echo "ON" || echo "OFF")
    local lutris_status=$([ "$_lutris" = "net.lutris.Lutris" ] && echo "ON" || echo "OFF")
    local heroic_status=$([ "$_heroic" = "com.heroicgameslauncher.hgl" ] && echo "ON" || echo "OFF")
    local pp_status=$([ "$_pp" = "com.vysp3r.ProtonPlus" ] && echo "ON" || echo "OFF")
    local stl_status=$([ "$_stl" = "com.valvesoftware.Steam.Utility.steamtinkerlaunch" ] && echo "ON" || echo "OFF")
    local sober_status=$([ "$_sobst" = "org.vinegarhq.Sober" ] && echo "ON" || echo "OFF")
    local disc_status=$([ "$_disc" = "com.discordapp.Discord" ] && echo "ON" || echo "OFF")
    local gmode_status=$([ "$_gmode" = "gamemode" ] && echo "ON" || echo "OFF")
    local gscope_status=$([ "$_gscope" = "gamescope" ] && echo "ON" || echo "OFF")
    local mhud_status=$([ "$_mhud" = "mangohud" ] && echo "ON" || echo "OFF")
    local govl_status=$([ "$_govl" = "goverlay" ] && echo "ON" || echo "OFF")
    local sboost_status=$([ "$_sboost" = "yes" ] && echo "ON" || echo "OFF")
    local dsplitm_status=$([ "$_dsplitm" = "yes" ] && echo "ON" || echo "OFF")
    local wivrn_status=$([ "$_wivrn" = "io.github.wivrn.wivrn" ] && echo "ON" || echo "OFF")
    local steer_status=$([ "$_steer" = "io.github.berarma.Oversteer" ] && echo "ON" || echo "OFF")


    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "Steam" "$msg109" $steam_status \
            "Lutris" "$msg110" $lutris_status \
            "Heroic Games Launcher" "$msg111" $heroic_status \
            "ProtonPlus" "$msg112" $pp_status \
            "SteamTinkerLaunch" "$msg113" $stl_status \
            "Sober" "$msg114" $sober_status \
            "Discord" "$msg130" $disc_status \
            "Gamemode" "$msg115" $gmode_status \
            "Gamescope" "$msg116" $gscope_status \
            "Mangohud" "$msg117" $mhud_status \
            "GOverlay" "$msg118" $govl_status \
            "Shader Booster" "$msg119" $sboost_status \
            "Disable SLM" "$msg041" $dsplitm_status \
            "Oversteer" "$msg145" $steer_status \
            "WiVRn" "$msg144" $wivrn_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"Steam"* ]] && _steam="steam" || _steam=""
        [[ "$selection" == *"Lutris"* ]] && _lutris="net.lutris.Lutris" || _lutris=""
        [[ "$selection" == *"Heroic Games Launcher"* ]] && _heroic="com.heroicgameslauncher.hgl" || _heroic=""
        [[ "$selection" == *"ProtonPlus"* ]] && _pp="com.vysp3r.ProtonPlus" || _pp=""
        [[ "$selection" == *"SteamTinkerLaunch"* ]] && _stl="com.valvesoftware.Steam.Utility.steamtinkerlaunch" || _stl=""
        [[ "$selection" == *"Sober"* ]] && _sobst="org.vinegarhq.Sober" || _sobst=""
        [[ "$selection" == *"Discord"* ]] && _disc="com.discordapp.Discord" || _gmode=""
        [[ "$selection" == *"Gamemode"* ]] && _gmode="gamemode" || _gmode=""
        [[ "$selection" == *"Gamescope"* ]] && _gscope="gamescope" || _gscope=""
        [[ "$selection" == *"Mangohud"* ]] && _mhud="mangohud" || _mhud=""
        [[ "$selection" == *"GOverlay"* ]] && _govl="goverlay" || _govl=""
        [[ "$selection" == *"Shader Booster"* ]] && _sboost="yes" || _sboost=""
        [[ "$selection" == *"Disable SLM"* ]] && _dsplitm="yes" || _dsplitm=""
        [[ "$selection" == *"WiVRn"* ]] && _wivrn="io.github.wivrn.wivrn" || _wivrn=""
        [[ "$selection" == *"Oversteer"* ]] && _steer="io.github.berarma.Oversteer" || _steer=""

        install_flatpak
        install_native
        sboost_t
        dsplitm_t
        if [[ -n "$flatpak_run" || -n "$dsplitm_run" || -n "$sboost_run" ]]; then
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        else
            whiptail --title "$msg006" --msgbox "$msg018" 8 78
        fi
    
    done

}

# installer functions
# native packages
install_native () {

    local _packages=($_steam $_gmode $_govl $_gscope $_mhud)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if [[ -n "$_steam" ]]; then
                cd $HOME
                wget https://cdn.fastly.steamstatic.com/client/installer/steam.deb
                sudo dpkg -i steam.deb
                rm steam.deb
            fi
        fi
        if [[ -n "$_gscope" ]]; then
            if command -v flatpak &> /dev/null; then
                flatpak install --or-update --system -y org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/23.08
            fi
        fi
        if [[ -n "$_mhud" ]]; then
            if command -v flatpak &> /dev/null; then
                flatpak install --or-update --system -y org.freedesktop.Platform.VulkanLayer.MangoHud
            fi
        fi
    fi
    install_n_lib

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_lutris $_heroic $_pp $_stl $_sobst $_disc $_wivrn $_steer)
    if [[ -n "$_flatpaks" ]] || [[ -n "$_steam" ]]; then
        if command -v flatpak &> /dev/null; then
            install_f_lib
            if [[ -n "$_steam" ]]; then
                flatpak install --or-update -u -y com.valvesoftware.Steam
                sed -i 's/^Name=Steam$/Name=Steam (Flatpak)/' "$HOME/.local/share/applications/com.valvesoftware.Steam.desktop"
            fi
            if [[ -n "$_steer" ]]; then
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
                sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
                whiptail --title "Oversteer" --msgbox "$msg146" 12 78
                xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices
            fi
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                flatpak_in_lib
                install_f_lib
                if [[ -n "$_steam" ]]; then
                    flatpak install --or-update -u -y com.valvesoftware.Steam
                    sed -i 's/^Name=Steam$/Name=Steam (Flatpak)/' "$HOME/.local/share/applications/com.valvesoftware.Steam.desktop"
                fi
                if [[ -n "$_steer" ]]; then
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
                    sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
                    whiptail --title "Oversteer" --msgbox "$msg146" 12 78
                    xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices
                fi
            else
                whiptail --title "$msg030" --msgbox "$msg132" 8 78
            fi
        fi
    fi

}

# shader booster
sboost_t () {

    if [[ -n "$_sboost" ]]; then
        cd $HOME
        sboost_run="1"
        if [ "$ID" == "cachyos" ]; then
            wget https://github.com/psygreg/shader-booster/releases/latest/download/patcher-cachy.fish
            chmod +x patcher-cachy.fish
            fish ./patcher-cachy.fish
            rm patcher-cachy.fish
        else
            wget https://github.com/psygreg/shader-booster/releases/latest/download/patcher.sh
            chmod +x patcher.sh
            ./patcher.sh
            rm patcher.sh
        fi
    fi

}

# split lock mitigation disabler
dsplitm_t () {

    if [[ -n "$_dsplitm" ]]; then
        dsplitm_run="1"
        if [ ! -f /etc/sysctl.d/99-splitlock.conf ]; then
            echo 'kernel.split_lock_mitigate=0' | sudo tee /etc/sysctl.d/99-splitlock.conf >/dev/null
            whiptail --title "$msg041" --msgbox "$msg022" 8 78
        else
            whiptail --title "$msg041" --msgbox "$msg043" 8 78
        fi
    fi

}

# runtime
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
det_langfile
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
. /etc/os-release
gsupermenu