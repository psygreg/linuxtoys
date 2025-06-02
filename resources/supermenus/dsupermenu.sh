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
aa_run=""
bb_run=""
# supermenu checklist
dsupermenu () {

    local code_status=$([ "$_code" = "code" ] && echo "ON" || echo "OFF")
    local codium_status=$([ "$_codium" = "com.vscodium.codium" ] && echo "ON" || echo "OFF")
    local nvim_status=$([ "$_nvim" = "neovim" ] && echo "ON" || echo "OFF")
    local idea_status=$([ "$_idea" = "idea" ] && echo "ON" || echo "OFF")
    local godot_status=$([ "$_godot" = "godot" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "VS Code" "$msg109" $code_status \
            "VSCodium" "$msg110" $codium_status \
            "NeoVim" "$msg111" $nvim_status \
            "IntelliJ IDEA" "$msg112" $idea_status \
            "Godot 4" "$msg113" $godot_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"VS Code"* ]] && _code="code" || _code=""
        [[ "$selection" == *"VSCodium"* ]] && _codium="com.vscodium.codium" || _codium=""
        [[ "$selection" == *"NeoVim"* ]] && _nvim="neovim" || _nvim=""
        [[ "$selection" == *"IntelliJ IDEA"* ]] && _idea="idea" || _idea=""
        [[ "$selection" == *"Godot 4"* ]] && _godot="godot" || _godot=""

        install_flatpak
        install_native
        others_t
        # adjust if rebooting is required for any software
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

    local _packages=($_code $_nvim)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if [[ -n "$_code" ]]; then
                cd $HOME
                wget https://vscode.download.prss.microsoft.com/dbazure/download/stable/848b80aeb52026648a8ff9f7c45a9b0a80641e2e/code_1.100.2-1747260578_amd64.deb
                sudo dpkg -i code_1.100.2-1747260578_amd64.deb
                rm code_1.100.2-1747260578_amd64.deb
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (code) ]]; then
                    continue
                fi
                sudo apt install -y $pak
            done
        elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
            if [[ -n "$_code" ]]; then
                if whiptail --title "$msg006" --yesno "$msg035" 8 78; then
                    cd $HOME
                    sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
                    sudo pacman-key --lsign-key 3056513887B78AEB
                    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'
                    sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'
                    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/linuxtoys-aur/resources/script.sed
                    sudo sed -i -f script.sed /etc/pacman.conf
                    sudo pacman -Sy
                    rm script.sed
                    sudo pacman -S --noconfirm visual-studio-code-bin
                else
                    whiptail --title "$msg006" --msgbox "Skipping Visual Studio Code installation." 8 78
                fi
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (code) ]]; then
                    continue
                fi
                sudo pacman -S --noconfirm $pak
            done
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [[ -n "$_code" ]]; then
                sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
                echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null
                sudo dnf check-update
                sudo dnf in code -y
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (code) ]]; then
                    continue
                fi
                sudo dnf in $pak -y
            done
        elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            if [[ -n "$_code" ]]; then
                sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
                echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" |sudo tee /etc/zypp/repos.d/vscode.repo > /dev/null
                sudo zypper install code -y
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (code) ]]; then
                    continue
                fi
                sudo zypper in $pak -y
            done
        fi
    fi

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_codium)
    if [[ -n "$_flatpaks" ]] || [[ -n "$_steam" ]]; then
        if command -v flatpak &> /dev/null; then
            for flat in "${_flatpaks[@]}"; do
                flatpak install --or-update -u -y $flat
            done
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
                    sudo apt install -y flatpak
                elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
                    sudo pacman -S --noconfirm flatpak
                fi
                flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
                flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
                for flat in "${_flatpaks[@]}"; do
                    flatpak install --or-update -u -y $flat
                done
            else
                whiptail --title "$msg030" --msgbox "$msg132" 8 78
            fi
        fi
    fi

}

# IntelliJ IDEA installer
idea_in () {

    # menu
    while :; do

        CHOICE=$(whiptail --title "IntelliJ IDEA" --menu "$msg067" 25 78 16 \
            "0" "Community Edition (free)" \
            "1" "Ultimate" \
            "2" "Cancel" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            break
        fi

        case $CHOICE in
        0) idea_ic ;;
        1) idea_iu ;;
        2 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

idea_ic () {

    cd $HOME
    wget https://download-cdn.jetbrains.com/idea/ideaIC-2025.1.1.1.tar.gz
    tar -xvzf ideaIC-2025.1.1.1.tar.gz
    mv idea-IC* idea-IC
    sudo cp -rf idea-IC /opt
    rm ideaIC-2025.1.1.1.tar.gz
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/intellijce.desktop
    sudo cp intellijce.desktop /usr/share/applications
    rm intellijce.desktop

}

idea_iu () {

    cd $HOME
    wget https://download-cdn.jetbrains.com/idea/ideaIU-2025.1.1.1.tar.gz
    tar -xvzf ideaIU-2025.1.1.1.tar.gz
    mv idea-IU* idea-IU
    sudo cp -rf idea-IU /opt
    rm ideaIU-2025.1.1.1.tar.gz
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/intellij.desktop
    sudo cp intellij.desktop /usr/share/applications
    rm intellij.desktop

}

# Godot Engine installer
godot_in () {

    # menu
    while :; do

        CHOICE=$(whiptail --title "Godot Engine" --menu "$msg067" 25 78 16 \
            "0" "Godot (Default)" \
            "1" "Godot .NET (C# Support)" \
            "2" "Cancel" 3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
            # Exit the script if the user presses Esc
            break
        fi

        case $CHOICE in
        0) godot_st ;;
        1) godot_shrp ;;
        2 | q) break ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

godot_st () {

    cd $HOME
    wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/5c13b07c-aad3-4bde-8712-9f0825758bb2?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T210343Z&X-Amz-Expires=300&X-Amz-Signature=2b5d1d411f853ce8c1eb9045af1b02f3567a4a8de13d754a3f1b3fce345a0051&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_linux.x86_64.zip&response-content-type=application%2Foctet-stream'
    unzip Godot_v4.4.1-stable_linux.x86_64.zip
    mv Godot_v4.4.1-stable_linux.x86_64 Godot
    sudo mkdir -p /opt/godot
    sudo cp Godot -f /opt/godot
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot.png
    sudo cp godot.png /opt/godot
    rm Godot
    rm godot.png
    rm Godot_v4.4.1-stable_linux.x86_64.zip
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot.desktop
    sudo cp godot.desktop /usr/share/applications
    rm godot.desktop

}

godot_shrp () {

    if [[ "$ID_LIKE" =~ (rhel|fedora) || "$ID" =~ (fedora|ubuntu|debian) || "$NAME" == "openSUSE Leap" ]]; then
        cd $HOME
        wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/8976b3a0-fb60-4d98-bd70-b623b9eaf9d3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T211639Z&X-Amz-Expires=300&X-Amz-Signature=11f42225a48cf9dea2a262ff4918e8c594b8494bd70ac108cf2e0b014fb8ac46&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_mono_linux_x86_64.zip&response-content-type=application%2Foctet-stream'
        mkdir -p godot
        unzip -d $HOME/godot Godot_v4.4.1-stable_mono_linux.x86_64.zip
        sudo cp -rf godot /opt/
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot.png
        sudo cp godot.png /opt/godot
        rm -rf godot
        rm godot.png
        rm Godot_v4.4.1-stable_mono_linux.x86_64.zip
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godotsharp.desktop
        sudo cp godotsharp.desktop /usr/share/applications
        rm godotsharp.desktop
        if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            sudo dnf in dotnet-sdk-9.0 -y
        elif [ "$ID" == "ubuntu" ]; then
            sudo apt install -y dotnet-sdk-9.0
        elif [ "$ID" == "debian" ]; then
            wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
            sudo dpkg -i packages-microsoft-prod.deb
            rm packages-microsoft-prod.deb
            sudo apt update
            sudo apt install -y dotnet-sdk-9.0
        elif [[ "$NAME" == "openSUSE Leap" ]]; then
            sudo zypper in libicu -y
            sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
            wget https://packages.microsoft.com/config/opensuse/15/prod.repo
            sudo mv prod.repo /etc/zypp/repos.d/microsoft-prod.repo
            sudo chown root:root /etc/zypp/repos.d/microsoft-prod.repo
            sudo zypper in dotnet-sdk-9.0 -y
        fi
    else
        whiptail --title "$msg030" --msgbox "$msg077" 8 78
    fi
    

}

# triggers for OS-agnostic installers
others_t () {

    if [[ -n "$_idea" ]]; then
        idea_in
    fi
    if [[ -n "$_godot" ]]; then
        godot_in
    fi

}

# runtime
det_langfile
current_ltver=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/ver)
source $HOME/.local/${langfile}_${current_ltver}
. /etc/os-release
dsupermenu