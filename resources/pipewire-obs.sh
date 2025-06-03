#!/bin/bash
# functions

# depcheck
depcheck_pipe () {

    local dependencies=(wireplumber)
    for dep in "${dependencies[@]}"; do
        if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
            if rpm -qi "$dep" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ]; then
                    sudo zypper in "$dep" -y
                else
                    sudo dnf in "$dep" -y
                fi
            fi
        elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
            if pacman -Qi "$dep" 2>/dev/null 1>&2; then
                continue
            else
                sudo pacman -S --noconfirm "$dep"
            fi
        elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if dpkg -s "$dep" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$dep"
            fi
        fi
    done

}

# install plugin for flatpak
flatpak_pipe () {

    if flatpak list --app | grep -q com.obsproject.Studio; then
        local ver="1.2.0"
        mkdir obspipe
        cd obspipe
        wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/${ver}/download/linux-pipewire-audio-${ver}-flatpak-30.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
        tar xvzf linux-pipewire-audio-${ver}-flatpak-30.tar.gz
        cp -rf linux-pipewire-audio $HOME/.var/app/com.obsproject.Studio/config/obs-studio/plugins/
        flatpak override --filesystem=xdg-run/pipewire-0 com.obsproject.Studio
        cd ..
        rm -rf obspipe
    else 
        whiptail --title "Installer" --msgbox "OBS Studio flatpak not installed." 8 78
    fi

}

# install plugin for native packages
native_pipe () {

    local ver="1.2.0"
    mkdir obspipe
    cd obspipe
    wget https://github.com/dimtpap/obs-pipewire-audio-capture/releases/${ver}/download/linux-pipewire-audio-${ver}.tar.gz || { echo "Download failed"; cd ..; rm -rf obspipe; return 1; }
    tar xvzf linux-pipewire-audio-${ver}.tar.gz
    cp -rf linux-pipewire-audio $HOME/.config/obs-studio/plugins/
    cd ..
    rm -rf obspipe

}

# native package checker
obscheck () {

    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        if rpm -qi "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    elif [[ "$ID" =~ (arch|cachyos) ]] || [[ "$ID_LIKE" =~ (arch) ]]; then
        if pacman -Q | grep -q "obs-studio"; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        if dpkg -s "obs-studio" 2>/dev/null 1>&2; then
            native_pipe
        else
            whiptail --title "Installer" --msgbox "OBS Studio not found." 8 78
        fi
    else
        whiptail --title "Installer" --msgbox "Invalid Operating System." 8 78
    fi

}

depcheck_pipe
# menu
while :; do

    CHOICE=$(whiptail --title "OBS Pipewire Audio Capture" --menu "Choose your OBS version:" 25 78 16 \
        "0" "Native" \
        "1" "Flatpak" \
        "2" "Cancel" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) obscheck ;;
    1) flatpak_pipe ;;
    2 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done