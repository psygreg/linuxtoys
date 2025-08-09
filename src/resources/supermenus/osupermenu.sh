#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
osupermenu () {

    local selection
    local selection_str
    local selected
    local search_item
    local item
    declare -a search_item=(
        "Zen Browser"
        "Chrome"
        "Onlyoffice"
        "Foliate"
        "MS Teams"
        "Anydesk"
        "Slack"
        "Figma"
        "Cohesion"
        "Darktable"
        "Pinta"
        "Krita"
        "GIMP"
        "Audacity"
        "Inkscape"
        "FreeCAD"
        "KiCad"
        "Kdenlive"
        "Blender"
        "DaVinci Resolve"
    )

    while true; do

        selection_str=$(zenity --list --checklist --title="Office Menu" \
            --column="" \
            --column="Apps" \
            FALSE "Zen Browser" \
            FALSE "Chrome" \
            FALSE "Onlyoffice" \
            FALSE "Foliate" \
            FALSE "MS Teams" \
            FALSE "Anydesk" \
            FALSE "Slack" \
            FALSE "Figma" \
            FALSE "Cohesion" \
            FALSE "Darktable" \
            FALSE "Pinta" \
            FALSE "Krita" \
            FALSE "GIMP" \
            FALSE "Audacity" \
            FALSE "Inkscape" \
            FALSE "FreeCAD" \
            FALSE "KiCad" \
            FALSE "Kdenlive" \
            FALSE "Blender" \
            FALSE "DaVinci Resolve" \
            --height=840 --width=300 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra selection <<< "$selection_str"

        for item in "${search_item[@]}"; do
            for selected in "${selection[@]}"; do
                if [[ "$selected" == "$item" ]]; then
                    case $item in
                        "Zen Browser") _zen="app.zen_browser.zen" ;;
                        "Chrome") _chrome="com.google.Chrome" ;;
                        "Onlyoffice") _oofice="org.onlyoffice.desktopeditors" ;;
                        "Foliate") _foli="com.github.johnfactotum.Foliate" ;;
                        "MS Teams") _msteams="com.github.IsmaelMartinez.teams_for_linux" ;;
                        "Anydesk") _anyd="com.anydesk.Anydesk" ;;
                        "Slack") _slck="com.slack.Slack" ;;
                        "Figma") _fig="1" ;;
                        "Cohesion") _notion="io.github.brunofin.Cohesion" ;;
                        "Darktable") _drktb="org.darktable.Darktable" ;;
                        "Pinta") _pnta="com.github.PintaProject.Pinta" ;;
                        "Krita") _krt="org.kde.krita" ;;
                        "GIMP") _gimp="org.gimp.GIMP" ;;
                        "Audacity") _audc="org.audacityteam.Audacity" ;;
                        "Inkscape") _inksc="org.inkscape.Inkscape" ;;
                        "FreeCAD") _fcad="org.freecad.FreeCAD" ;;
                        "KiCad") _kcad="org.kicad.KiCad" ;;
                        "Kdenlive") _klive="org.kde.kdenlive" ;;
                        "Blender") _blender="org.blender.Blender" ;;
                        "DaVinci Resolve") _drslv="yes" ;;
                    esac
                fi
            done
        done

        install_flatpak
        install_native
        figma_t
        if [[ -n "$flatpak_run" ]]; then
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

    local _packages=($_drslv $_fial)
    cd $HOME
    if [[ -n "$_packages" ]]; then
        if [[ -n "$_drslv" ]]; then
            zenwrn "$msg034"
            davincimenu
        fi
    fi
    _install_

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_oofice $_anyd $_fcad $_gimp $_inksc $_notion $_msteams $_slck $_chrome $_zen $_drktb $_foli $_blender $_kcad $_klive $_audc)
    if [[ -n "$_flatpaks" ]]; then
        if command -v flatpak &> /dev/null; then
            flatpak_in_lib
            _flatpak_
        else
            if zenity --question --text "$msg085" --width 360 --height 300; then
                flatpak_run="1"
                flatpak_in_lib
                _flatpak_
            else
                nonfatal "$msg132"
                return 1
            fi
        fi
        if [[ -n "$_gimp" ]]; then
            if zenity --question --text "$msg253" --width 360 --height 300; then
                zeninf "$msg254"
                flatpak run org.gimp.GIMP & sleep 1
                PID=($(pgrep -f "gimp"))
                if [ -z "$PID" ]; then
                    echo "Failed to find Flatpak process."
                    exit 1
                fi
                echo "Found Flatpak app running as PID $PID"
                sleep 20
                for ID in "${PID[@]}"; do
                    kill "$ID"
                done
                wait "$PID" 2>/dev/null
                git clone https://github.com/Diolinux/PhotoGIMP.git
                cd PhotoGIMP
                cp -rf .config/* $HOME/.config/
                cp -rf .local/* $HOME/.local/
                cd ..
                rm -rf PhotoGIMP
            fi
        fi
    fi

}

# figma installer
figma_t () {

    if [[ -n "$_fig" ]]; then
        cd $HOME
        local tag=$(curl -s https://api.github.com/repos/Figma-Linux/figma-linux/releases/latest | grep '"tag_name"' | cut -d '"' -f4 | sed 's/^v//')
        wget https://github.com/Figma-Linux/figma-linux/releases/download/v${tag}/figma-linux_${tag}_linux_x86_64.AppImage
        chmod +x figma-linux-*.AppImage
        sudo ./figma-linux-*.AppImage -i
        sleep 1
        rm figma-linux-*.AppImage
    fi

}

# davinci resolve menu
davincimenu () {

    # menu
    while true; do

        CHOICE=$(zenity --list --title "DaVinci Resolve" \
            --column="" \
            "$msg231" \
            "$msg232" \
            "$msg070" \
            --height=330 --width=300)

        if [ $? -ne 0 ]; then
            exit 0
        fi

        case $CHOICE in
        "$msg231") davinciboxd && return ;;
        "$msg232") davincinatd && return ;;
        "$msg070") break ;;
        *) echo "Invalid Option" ;;
        esac
        
    done

}

davincinatd () {

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
    elif [[ "$ID_LIKE" == *suse* ]]; then
        wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autoresolverpm.sh
        chmod +x autoresolverpm.sh
        ./autoresolverpm.sh
        rm autoresolverpm.sh
    fi

}

davinciboxd () {

    wget https://raw.githubusercontent.com/psygreg/autoresolvedeb/refs/heads/main/linuxtoys/autodavincibox.sh
    chmod +x autodavincibox.sh
    ./autodavincibox.sh
    rm autodavincibox.sh

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
osupermenu
