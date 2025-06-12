#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
osupermenu () {

    local oofice_status=$([ "$_oofice" = "org.onlyoffice.desktopeditors" ] && echo "ON" || echo "OFF")
    local msteams_status=$([ "$_msteams" = "com.github.IsmaelMartinez.teams_for_linux" ] && echo "ON" || echo "OFF")
    local anyd_status=$([ "$_anyd" = "com.anydesk.Anydesk" ] && echo "ON" || echo "OFF")
    local slck_status=$([ "$_slck" = "com.slack.Slack" ] && echo "ON" || echo "OFF")
    local notion_status=$([ "$_notion" = "io.github.brunofin.Cohesion" ] && echo "ON" || echo "OFF")
    local gimp_status=$([ "$_gimp" = "org.gimp.GIMP" ] && echo "ON" || echo "OFF")
    local inksc_status=$([ "$_inksc" = "org.inkscape.Inkscape" ] && echo "ON" || echo "OFF")
    local fcad_status=$([ "$_fcad" = "org.freecad.FreeCAD" ] && echo "ON" || echo "OFF")
    local drslv_status=$([ "$_drslv" = "yes" ] && echo "ON" || echo "OFF")
    local blender_status=$([ "$_blender" = "org.blender.Blender" ] && echo "ON" || echo "OFF")
    local fial_status=$([ "$_fial" = "yes" ] && echo "ON" || echo "OFF")
    local chrome_status=$([ "$_chrome" = "com.google.Chrome" ] && echo "ON" || echo "OFF")
    local zen_status=$([ "$_zen" = "app.zen_browser.zen" ] && echo "ON" || echo "OFF")
    local drktb_status=$([ "$_drktb" = "org.darktable.Darktable" ] && echo "ON" || echo "OFF")
    local foli_status=$([ "$_foli" = "com.github.johnfactotum.Foliate" ] && echo "ON" || echo "OFF")

    while :; do
    
        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "Zen" "$msg128" $zen_status \
            "Chrome" "$msg129" $chrome_status \
            "Onlyoffice" "$msg099" $oofice_status \
            "Foliate" "$msg149" $foli_status \
            "MS Teams" "$msg100" $msteams_status \
            "Anydesk" "$msg101" $anyd_status \
            "Slack" "$msg102" $slck_status \
            "Cohesion" "$msg103" $notion_status \
            "Darktable" "$msg148" $drktb_status \
            "GIMP" "$msg104" $gimp_status \
            "Inkscape" "$msg105" $inksc_status \
            "FreeCAD" "$msg106" $fcad_status \
            "Blender" "$msg159" $blender_status \
            "DaVinci Resolve" "$msg107" $drslv_status \
            "FireAlpaca" "$msg108" $fial_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"Onlyoffice"* ]] && _oofice="org.onlyoffice.desktopeditors" || _oofice=""
        [[ "$selection" == *"MS Teams"* ]] && _msteams="com.github.IsmaelMartinez.teams_for_linux" || _msteams=""
        [[ "$selection" == *"Anydesk"* ]] && _anyd="com.anydesk.Anydesk" || _anyd=""
        [[ "$selection" == *"Slack"* ]] && _slck="com.slack.Slack" || _slck=""
        [[ "$selection" == *"Cohesion"* ]] && _notion="io.github.brunofin.Cohesion" || _notion=""
        [[ "$selection" == *"Darktable"* ]] && _drktb="org.darktable.Darktable" || _drktb=""
        [[ "$selection" == *"GIMP"* ]] && _gimp="org.gimp.GIMP" || _gimp=""
        [[ "$selection" == *"Inkscape"* ]] && _inksc="org.inkscape.Inkscape" || _inksc=""
        [[ "$selection" == *"FreeCAD"* ]] && _fcad="org.freecad.FreeCAD" || _fcad=""
        [[ "$selection" == *"DaVinci Resolve"* ]] && _drslv="yes" || _drslv=""
        [[ "$selection" == *"Blender"* ]] && _blender="org.blender.Blender" || _blender=""
        [[ "$selection" == *"FireAlpaca"* ]] && _fial="yes" || _fial=""
        [[ "$selection" == *"Chrome"* ]] && _chrome="com.google.Chrome" || _chrome=""
        [[ "$selection" == *"Zen"* ]] && _zen="app.zen_browser.zen" || _zen=""
        [[ "$selection" == *"Foliate"* ]] && _foli="com.github.johnfactotum.Foliate" || _foli=""

        install_flatpak
        install_native
        if [[ -n "$flatpak_run" ]]; then
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        else
            local title="$msg006"
            local msg="$msg018"
            _msgbox_
        fi
        break
    
    done

}

# installer functions
# native packages
install_native () {

    local _packages=($_drslv $_fial)
    cd $HOME
    if [[ -n "$_packages" ]]; then
        if [[ -n "$_drslv" ]]; then
                local title="$msg006"
                local msg="$msg034"
                _msgbox_
            if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvedeb.sh
                chmod +x autoresolvedeb.sh
                ./autoresolvedeb.sh
                rm autoresolvedeb.sh
            elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvepkg.sh
                chmod +x autoresolvepkg.sh
                ./autoresolvepkg.sh
                rm autoresolvepkg.sh
            elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" = "fedora" ]; then
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
                chmod +x autoresolverpm.sh
                ./autoresolverpm.sh
                rm autoresolverpm.sh
            elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
                chmod +x autoresolverpm.sh
                ./autoresolverpm.sh
                rm autoresolverpm.sh
            fi
        fi
        if [[ -n "$_fial" ]]; then   
            if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
                wget https://github.com/psygreg/firealpaca-deb/releases/latest/download/installer.sh
                chmod +x installer.sh
                ./installer.sh
                rm installer.sh
            else
                local title="$msg030"
                local msg="$msg077"
                _msgbox_
            fi
        fi   
    fi
    _install_

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_oofice $_anyd $_fcad $_gimp $_inksc $_notion $_msteams $_slck $_chrome $_zen $_drktb $_foli $_blender)
    if [[ -n "$_flatpaks" ]]; then
        if command -v flatpak &> /dev/null; then
            flatpak_in_lib
            _flatpak_
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                flatpak_in_lib
                _flatpak_
            else
                local title="$msg030"
                local msg="$msg132"
                _msgbox_
            fi
        fi
    fi

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
osupermenu