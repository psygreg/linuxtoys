#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
dsupermenu () {

    local code_status=$([ "$_code" = "code" ] && echo "ON" || echo "OFF")
    local codium_status=$([ "$_codium" = "com.vscodium.codium" ] && echo "ON" || echo "OFF")
    local nvim_status=$([ "$_nvim" = "neovim" ] && echo "ON" || echo "OFF")
    local idea_status=$([ "$_idea" = "idea" ] && echo "ON" || echo "OFF")
    local nvm_status=$([ "$_nvm" = "nvm" ] && echo "ON" || echo "OFF")
    local pyenv_status=$([ "$_pyenv" = "pyenv" ] && echo "ON" || echo "OFF")
    local godot_status=$([ "$_godot" = "godot" ] && echo "ON" || echo "OFF")
    local unity_status=$([ "$_unity" = "unityhub" ] && echo "ON" || echo "OFF")
    local dotnet_status=$([ "$_dotnet" = "dotnet-sdk-9.0" ] && echo "ON" || echo "OFF")
    local java_status=$([ "$_java" = "java" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "VS Code" "$msg141" $code_status \
            "VSCodium" "$msg142" $codium_status \
            "NeoVim" "$msg140" $nvim_status \
            "IntelliJ IDEA" "$msg138" $idea_status \
            "NodeJS" "+ Node Version Manager" $nvm_status \
            "Python" "$msg134" $pyenv_status \
            "C#" "Microsoft .NET SDK" $dotnet_status \
            "Java" "OpenJDK/JRE" $java_status \
            "Godot 4" "$msg139" $godot_status \
            "Unity Hub" "$msg137" $unity_status \
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
        [[ "$selection" == *"NodeJS"* ]] && _nvm="nodejs" || _nvm=""
        [[ "$selection" == *"Python"* ]] && _pyenv="pyenv" || _pyenv=""
        [[ "$selection" == *"Godot 4"* ]] && _godot="godot" || _godot=""
        [[ "$selection" == *"Unity Hub"* ]] && _unity="unityhub" || _unity=""
        [[ "$selection" == *"C#"* ]] && _dotnet="dotnet-sdk-9.0" || _dotnet=""
        [[ "$selection" == *"Java"* ]] && _java="java" || _java=""


        install_flatpak
        install_native
        others_t
        # adjust if rebooting is required for any software
        if [[ -n "$flatpak_run" || -n "$_pyenv" || -n "$_nvm" ]]; then
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        else
            local title="$msg006"
            local msg="$msg018"
            _msgbox_
        fi
    
    done

}

# installer functions
# native packages
install_native () {

    local _packages=($_code $_nvim $_nvm $_pyenv $_unity $_dotnet)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if [[ -n "$_code" ]]; then
                cd $HOME
                wget https://vscode.download.prss.microsoft.com/dbazure/download/stable/848b80aeb52026648a8ff9f7c45a9b0a80641e2e/code_1.100.2-1747260578_amd64.deb
                sudo dpkg -i code_1.100.2-1747260578_amd64.deb
                rm code_1.100.2-1747260578_amd64.deb
            fi
            if [[ -n "$_pyenv" ]]; then
                insta make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
            fi
            if [[ -n "$_unity" ]]; then
                wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /usr/share/keyrings/Unity_Technologies_ApS.gpg > /dev/null
                sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" > /etc/apt/sources.list.d/unityhub.list'
                sudo apt update
            fi
            if [[ -n "$_dotnet" && "$ID" == "debian" ]]; then
                wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
                sudo dpkg -i packages-microsoft-prod.deb
                rm packages-microsoft-prod.deb
                sudo apt update
            fi
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]]; then
            if [[ -n "$_code" ]]; then
                if whiptail --title "$msg006" --yesno "$msg035" 8 78; then
                    chaotic_aur_lib
                else
                    local title="$msg006"
                    local msg="Skipping Visual Studio Code installation."
                    _msgbox_
                fi
            fi
            if [[ -n "$_pyenv" ]]; then
                insta base-devel openssl zlib xz tk
            fi
            if [[ -n "$_unity" ]]; then
                local title="Unity Hub"
                local msg="$msg077"
                _msgbox_
            fi
            if [[ -n "$_dotnet" ]]; then
                local title=".NET SDK"
                local msg="$msg077"
                _msgbox_
            fi
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [[ -n "$_code" ]]; then
                sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
                echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null
                sudo dnf check-update
                insta code 
            fi
            if [[ -n "$_pyenv" ]]; then
                insta make gcc patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel libuuid-devel gdbm-libs libnsl2 -y
            fi
            if [[ -n "$_unity" ]]; then
                if [ "$ID" == "rhel" ]; then
                    sudo sh -c 'echo -e "[unityhub]\nname=Unity Hub\nbaseurl=https://hub.unity3d.com/linux/repos/rpm/stable\nenabled=1\ngpgcheck=1\ngpgkey=https://hub.unity3d.com/linux/repos/rpm/stable/repodata/repomd.xml.key\nrepo_gpgcheck=1" > /etc/yum.repos.d/unityhub.repo'
                    sudo yum check-update
                    sudo yum install unityhub
                else
                    local title="Unity Hub"
                    local msg="$msg077"
                    _msgbox_
                fi
            fi
        elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            if [[ -n "$_code" ]]; then
                sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
                echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" |sudo tee /etc/zypp/repos.d/vscode.repo > /dev/null
                insta code
            fi
            if [[ -n "$_pyenv" ]]; then
                insta gcc automake bzip2 libbz2-devel xz xz-devel openssl-devel ncurses-devel readline-devel zlib-devel tk-devel libffi-devel sqlite3-devel gdbm-devel make findutils patch -y
            fi
            if [[ -n "$_dotnet" ]]; then
                if [ "$NAME" == "openSUSE Leap" ]; then
                    insta libicu
                    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
                    wget https://packages.microsoft.com/config/opensuse/15/prod.repo
                    sudo mv prod.repo /etc/zypp/repos.d/microsoft-prod.repo
                    sudo chown root:root /etc/zypp/repos.d/microsoft-prod.repo
                    insta dotnet-sdk-9.0
                else
                    local title=".NET SDK"
                    local msg="$msg077"
                    _msgbox_
                fi
            fi
        fi
        _install_
    fi

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_codium)
    if [[ -n "$_flatpaks" ]] || [[ -n "$_steam" ]]; then
        if command -v flatpak &> /dev/null; then
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
            return
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
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/intellijce.desktop
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
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/intellij.desktop
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
            return
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
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/godot.png
    sudo cp godot.png /opt/godot
    rm Godot
    rm godot.png
    rm Godot_v4.4.1-stable_linux.x86_64.zip
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/godot.desktop
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
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/godot.png
        sudo cp godot.png /opt/godot
        rm -rf godot
        rm godot.png
        rm Godot_v4.4.1-stable_mono_linux.x86_64.zip
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/godotsharp.desktop
        sudo cp godotsharp.desktop /usr/share/applications
        rm godotsharp.desktop
        if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            insta dotnet-sdk-9.0
        elif [ "$ID" == "ubuntu" ]; then
            insta dotnet-sdk-9.0
        elif [ "$ID" == "debian" ]; then
            wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
            sudo dpkg -i packages-microsoft-prod.deb
            rm packages-microsoft-prod.deb
            sudo apt update
            insta dotnet-sdk-9.0
        elif [[ "$NAME" == "openSUSE Leap" ]]; then
            sudo insta libicu
            sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
            wget https://packages.microsoft.com/config/opensuse/15/prod.repo
            sudo mv prod.repo /etc/zypp/repos.d/microsoft-prod.repo
            sudo chown root:root /etc/zypp/repos.d/microsoft-prod.repo
            insta dotnet-sdk-9.0 
        fi
    else
        local title="$msg030"
        local msg="$msg077"
        _msgbox_
    fi
    

}

# java JDK + JRE installation
jdk_install () {

    local javas=($_jdk8 $_jdk11 $_jdk17 $_jdk21 $_jdk24)
    for jav in "${javas[@]}"; do
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            insta openjdk-${jav}-jdk openjdk-${jav}-jre
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [ $jav == "8" ]; then
                insta java-1.8.0-openjdk java-1.8.0-openjdk-devel
                continue
            fi
            insta java-${jav}-openjdk java-${jav}-openjdk-devel
        elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            insta java-${jav}-openjdk java-${jav}-openjdk-devel
        fi
    done

}

java_in () {

    local jdk8_status=$([ "$_jdk8" = "8" ] && echo "ON" || echo "OFF")
    local jdk11_status=$([ "$_jdk11" = "11" ] && echo "ON" || echo "OFF")
    local jdk17_status=$([ "$_jdk17" = "17" ] && echo "ON" || echo "OFF")
    local jdk21_status=$([ "$_jdk21" = "21" ] && echo "ON" || echo "OFF")
    local jdk24_status=$([ "$_jdk24" = "24" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "Java 8" "LTS" $jdk8_status \
            "Java 11" "LTS" $jdk11_status \
            "Java 17" "LTS" $jdk17_status \
            "Java 21" "LTS" $jdk21_status \
            "Java 24" "Latest" $jdk24_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            return
        fi

        [[ "$selection" == *"Java 8"* ]] && _jdk8="8" || _jdk8=""
        [[ "$selection" == *"Java 11"* ]] && _jdk11="11" || _jdk11=""
        [[ "$selection" == *"Java 17"* ]] && _jdk17="17" || _jdk17=""
        [[ "$selection" == *"Java 21"* ]] && _jdk21="21" || _jdk21=""
        [[ "$selection" == *"Java 24"* ]] && _jdk24="24" || _jdk24=""

        jdk_install

    done

}

# triggers for OS-agnostic installers
others_t () {

    if [[ -n "$_idea" ]]; then
        idea_in
    fi
    if [[ -n "$_godot" ]]; then
        godot_in
    fi
    if [[ -n "$_nvm" ]]; then
        wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
        rm install.sh
        npm i --global yarn
        # basic usage instruction prompt
        local title="$msg006"
        local msg="$msg136"
        _msgbox_
        xdg-open https://github.com/nvm-sh/nvm?tab=readme-ov-file#usage
    fi
    if [[ -n "$_pyenv" ]]; then
        # pyenv and python build requirements installation
        curl -fsSL https://pyenv.run | bash
        if [[ -f "${HOME}/.bash_profile" ]]; then
            echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
            echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
            echo 'eval "$(pyenv init - bash)"' >> ~/.bash_profile
        elif [[ -f "$HOME/.profile" ]]; then
            echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
            echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
            echo 'eval "$(pyenv init - bash)"' >> ~/.profile
        fi
        if [[ -f "$HOME/.zshrc" ]]; then
            echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
            echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
            echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc
        fi
        git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
        echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
        # basic usage instruction prompt
        local title="$msg006"
        local msg="$msg135"
        _msgbox_
        xdg-open https://github.com/pyenv/pyenv?tab=readme-ov-file#usage
        xdg-open https://github.com/pyenv/pyenv-virtualenv?tab=readme-ov-file#usage
    fi
    if [[ -n "$_java" ]]; then
        java_in
    fi

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
dsupermenu