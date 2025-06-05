#!/bin/bash

# determine language
det_langfile () {

    local lang="${LANG:0:2}"
    local available=("pt")
    local ulang=""

    if [[ " ${available[*]} " == *"$lang"* ]]; then
        ulang="$lang"
    else
        ulang="en"
    fi
    if [ $ulang == "pt" ]; then
        langfile=".ltlang-pt"
    else
        langfile=".ltlang-en"
    fi

}

export NEWT_COLORS='
    root=white,blue
    border=black,lightgray
    window=black,lightgray
    shadow=black,gray
    title=black,lightgray
    button=black,cyan
    actbutton=white,blue
    checkbox=black,lightgray
    actcheckbox=black,cyan
    entry=black,lightgray
    label=black,lightgray
    listbox=black,lightgray
    actlistbox=black,cyan
    textbox=black,lightgray
    acttextbox=black,cyan
    helpline=white,blue
    roottext=black,lightgray
'

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
        [[ "$selection" == *"FireAlpaca"* ]] && _fial="yes" || _fial=""
        [[ "$selection" == *"Chrome"* ]] && _chrome="com.google.Chrome" || _chrome=""
        [[ "$selection" == *"Zen"* ]] && _zen="app.zen_browser.zen" || _zen=""
        [[ "$selection" == *"Foliate"* ]] && _foli="com.github.johnfactotum.Foliate" || _foli=""

        install_flatpak
        install_native
        if [[ -n "$flatpak_run" ]]; then
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        else
            whiptail --title "$msg006" --msgbox "$msg018" 8 78
        fi
    
    done

}

# installer functions
# native packages
install_native () {

    local _packages=($_drslv $_fial)
    cd $HOME
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if [[ -n "$_drslv" ]]; then
                whiptail --title "$msg006" --msgbox "$msg034" 8 78
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvedeb.sh
                chmod +x autoresolvedeb.sh
                ./autoresolvedeb.sh
                rm autoresolvedeb.sh
            fi
            if [[ -n "$_fial" ]]; then
                wget https://github.com/psygreg/firealpaca-deb/releases/latest/download/installer.sh
                chmod +x installer.sh
                ./installer.sh
                rm installer.sh
            fi
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
            if [[ -n "$_drslv" ]]; then
                whiptail --title "$msg006" --msgbox "$msg034" 12 78
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolvepkg.sh
                chmod +x autoresolvepkg.sh
                ./autoresolvepkg.sh
                rm autoresolvepkg.sh
            fi
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" = "fedora" ]; then
            if [[ -n "$_drslv" ]]; then
                whiptail --title "$msg006" --msgbox "$msg034" 8 78
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
                chmod +x autoresolverpm.sh
                ./autoresolverpm.sh
                rm autoresolverpm.sh
            fi
        elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            if [[ -n "$_drslv" ]]; then
                whiptail --title "$msg006" --msgbox "$msg034" 8 78
                wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
                chmod +x autoresolverpm.sh
                ./autoresolverpm.sh
                rm autoresolverpm.sh
            fi
        fi
    fi
    install_n_lib

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_oofice $_anyd $_fcad $_gimp $_inksc $_notion $_msteams $_slck $_chrome $_zen $_drktb $_foli)
    if [[ -n "$_flatpaks" ]]; then
        if command -v flatpak &> /dev/null; then
            install_f_lib
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                flatpak_in_lib
                install_f_lib
            else
                whiptail --title "$msg030" --msgbox "$msg132" 8 78
            fi
        fi
    fi

}

# runtime
det_langfile
current_ltver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
source $HOME/.local/${langfile}_${current_ltver}
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/linuxtoys.lib)
osupermenu