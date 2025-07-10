#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
dsupermenu () {

    local code_status=$([ "$_code" = "code" ] && echo "ON" || echo "OFF")
    local codium_status=$([ "$_codium" = "com.vscodium.codium" ] && echo "ON" || echo "OFF")
    local nvim_status=$([ "$_nvim" = "neovim" ] && echo "ON" || echo "OFF")
    local jb_status=$([ "$_jb" = "1" ] && echo "ON" || echo "OFF")
    local nvm_status=$([ "$_nvm" = "nodejs" ] && echo "ON" || echo "OFF")
    local mvn_status=$([ "$_mvn" = "maven" ] && echo "ON" || echo "OFF")
    local pyenv_status=$([ "$_pyenv" = "pyenv" ] && echo "ON" || echo "OFF")
    local godot_status=$([ "$_godot" = "godot" ] && echo "ON" || echo "OFF")
    local unity_status=$([ "$_unity" = "unityhub" ] && echo "ON" || echo "OFF")
    local dotnet_status=$([ "$_dotnet" = "dotnet-sdk-9.0" ] && echo "ON" || echo "OFF")
    local java_status=$([ "$_java" = "java" ] && echo "ON" || echo "OFF")
    local droidstd_status=$([ "$_droidstd" = "droidstd" ] && echo "ON" || echo "OFF")
    local omb_status=$([ "$_omb" = "1" ] && echo "ON" || echo "OFF")
    local insomnia_status=$([ "$_insomnia" = "rest.insomnia.Insomnia" ] && echo "ON" || echo "OFF")
    local httpie_status=$([ "$_httpie" = "io.httpie.Httpie" ] && echo "ON" || echo "OFF")
    local postman_status=$([ "$_postman" = "getpostman.Postman" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "VS Code" "$msg141" $code_status \
            "VSCodium" "$msg142" $codium_status \
            "NeoVim" "$msg140" $nvim_status \
            "Jetbrains" "$msg162" $jb_status \
            "OhMyBash" "$msg226" $omb_status \
            "NodeJS" "+ Node Version Manager" $nvm_status \
            "Maven" "$msg178" $mvn_status \
            "Python" "$msg134" $pyenv_status \
            "C#" "Microsoft .NET SDK" $dotnet_status \
            "Java" "OpenJDK/JRE" $java_status \
            "Android Studio" "$msg206" $droidstd_status \
            "Godot 4" "$msg139" $godot_status \
            "Unity Hub" "$msg137" $unity_status \
            "Insomnia" "$msg245" $insomnia_status \
            "Httpie" "$msg246" $httpie_status \
            "Postman" "$msg246" $postman_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"VS Code"* ]] && _code="code" || _code=""
        [[ "$selection" == *"VSCodium"* ]] && _codium="com.vscodium.codium" || _codium=""
        [[ "$selection" == *"NeoVim"* ]] && _nvim="neovim" || _nvim=""
        [[ "$selection" == *"Jetbrains"* ]] && _jb="1" || _jb=""
        [[ "$selection" == *"NodeJS"* ]] && _nvm="nodejs" || _nvm=""
        [[ "$selection" == *"Maven"* ]] && _mvn="maven" || _mvn=""
        [[ "$selection" == *"Python"* ]] && _pyenv="pyenv" || _pyenv=""
        [[ "$selection" == *"Godot 4"* ]] && _godot="godot" || _godot=""
        [[ "$selection" == *"Unity Hub"* ]] && _unity="unityhub" || _unity=""
        [[ "$selection" == *"C#"* ]] && _dotnet="dotnet-sdk-9.0" || _dotnet=""
        [[ "$selection" == *"Java"* ]] && _java="java" || _java=""
        [[ "$selection" == *"Android Studio"* ]] && _droidstd="droidstd" || _droidstd=""
        [[ "$selection" == *"OhMyBash"* ]] && _omb="1" || _omb=""
        [[ "$selection" == *"Insomnia"* ]] && _insomnia="rest.insomnia.Insomnia" || _insomnia=""
        [[ "$selection" == *"Httpie"* ]] && _httpie="io.httpie.Httpie" || _insomnia=""
        [[ "$selection" == *"Postman"* ]] && _postman="getpostman.Postman" || _postman=""

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
        break
    
    done

}

# installer functions
# native packages
install_native () {

    local _packages=($_code $_nvim $_nvm $_mvn $_pyenv $_unity $_dotnet)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
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
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            if [[ -n "$_code" ]]; then
                if whiptail --title "$msg006" --yesno "$msg035" 8 78; then
                    chaotic_aur_lib
                    insta visual-studio-code-bin
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
        elif [[ "$ID_LIKE" == *suse* ]]; then
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

    local _flatpaks=($_codium $_insomnia $_httpie $_postman)
    if [[ -n "$_flatpaks" ]] || [[ -n "$_steam" ]]; then
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
    # first install
    if [ ! -d "/opt/godot" ]; then
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
    else # update
        wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/5c13b07c-aad3-4bde-8712-9f0825758bb2?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T210343Z&X-Amz-Expires=300&X-Amz-Signature=2b5d1d411f853ce8c1eb9045af1b02f3567a4a8de13d754a3f1b3fce345a0051&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_linux.x86_64.zip&response-content-type=application%2Foctet-stream'
        unzip Godot_v4.4.1-stable_linux.x86_64.zip
        mv Godot_v4.4.1-stable_linux.x86_64 Godot
        sudo cp Godot -f /opt/godot
        rm Godot
        rm Godot_v4.4.1-stable_linux.x86_64.zip
    fi
    

}

godot_shrp () {

    if [[ "$ID_LIKE" =~ (rhel|fedora) || "$ID" =~ (fedora|ubuntu|debian) || "$NAME" == "openSUSE Leap" ]]; then
        cd $HOME
        # first install
        if [ ! -d "/opt/godot" ]; then
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
        else # update
            wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/8976b3a0-fb60-4d98-bd70-b623b9eaf9d3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T211639Z&X-Amz-Expires=300&X-Amz-Signature=11f42225a48cf9dea2a262ff4918e8c594b8494bd70ac108cf2e0b014fb8ac46&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_mono_linux_x86_64.zip&response-content-type=application%2Foctet-stream'
            mkdir -p godot
            unzip -d $HOME/godot Godot_v4.4.1-stable_mono_linux.x86_64.zip
            sudo rm -rf /opt/godot
            sudo cp -rf godot /opt/
            rm -rf godot
            rm Godot_v4.4.1-stable_mono_linux.x86_64.zip
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
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            insta openjdk-${jav}-jdk openjdk-${jav}-jre
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [ $jav == "8" ]; then
                insta java-1.8.0-openjdk java-1.8.0-openjdk-devel
                continue
            fi
            insta java-${jav}-openjdk java-${jav}-openjdk-devel
        elif [[ "$ID_LIKE" == *suse* ]]; then
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

    if [[ -n "$_jb" ]]; then
        source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/subscripts/jetbrainsmenu.lib)
        jetbrains_menu
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
    if [[ -n "$_droidstd" ]]; then
        local subscript="android-studio-in"
        _invoke_
    fi
    if [[ -n "$_omb" ]]; then
        bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)"
    fi

}

# intellij idea
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
        0) idea_ic && return ;;
        1) idea_iu && return ;;
        2 | q) return ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

# jetbrains trigger
jetbrains_t () {

    if [[ -n "$_tb" ]]; then
        if whiptail --title "Jetbrains Toolbox" --yesno "$msg173" 12 78; then
            _pycharm=""
            _idea=""
            _wstorm=""
            _rider=""
            _clion=""
            _rustr=""
            _rubym=""
            _datag=""
            _phpstorm=""
            _goland=""
            toolbox_in
            return
        fi
    fi
    if [[ -n "$_pycharm" ]]; then
      pycharm_in
    fi
    if [[ -n "$_idea" ]]; then
      idea_in
    fi
    if [[ -n "$_wstorm" ]]; then
      webstorm_in
    fi
    if [[ -n "$_rider" ]]; then
      rider_in
    fi
    if [[ -n "$_clion" ]]; then
      clion_in
    fi
    if [[ -n "$_rustr" ]]; then
      rustrover_in
    fi
    if [[ -n "$_rubym" ]]; then
      rubymine_in
    fi
    if [[ -n "$_datag" ]]; then
      datagrip_in
    fi
    if [[ -n "$_phpstorm" ]]; then
      phpstorm_in
    fi
    if [[ -n "$_goland" ]]; then
      goland_in
    fi

}


# Jetbrains menu
jetbrains_menu () {

    local pycharm_status=$([ "$_pycharm" = "1" ] && echo "ON" || echo "OFF")
    local idea_status=$([ "$_idea" = "1" ] && echo "ON" || echo "OFF")
    local webstorm_status=$([ "$_wstorm" = "1" ] && echo "ON" || echo "OFF")
    local rider_status=$([ "$_rider" = "1" ] && echo "ON" || echo "OFF")
    local clion_status=$([ "$_clion" = "1" ] && echo "ON" || echo "OFF")
    local rustrover_status=$([ "$_rustr" = "1" ] && echo "ON" || echo "OFF")
    local rubymine_status=$([ "$_rubym" = "1" ] && echo "ON" || echo "OFF")
    local datagrip_status=$([ "$_datag" = "1" ] && echo "ON" || echo "OFF")
    local phpstorm_status=$([ "$_phpstorm" = "1" ] && echo "ON" || echo "OFF")
    local goland_status=$([ "$_goland" = "1" ] && echo "ON" || echo "OFF")
    local toolbox_status=$([ "$_tb" = "1" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "PyCharm" "$msg163" $pycharm_status \
            "IntelliJ IDEA" "$msg138" $idea_status \
            "WebStorm" "$msg164" $webstorm_status \
            "Rider" "$msg165" $rider_status \
            "CLion" "$msg166" $clion_status \
            "RustRover" "$msg167" $rustrover_status \
            "RubyMine" "$msg168" $rubymine_status \
            "DataGrip" "$msg169" $datagrip_status \
            "PhpStorm" "$msg170" $phpstorm_status \
            "GoLand" "$msg171" $goland_status \
            "Toolbox" "$msg172" $toolbox_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
          return
        fi

        [[ "$selection" == *"PyCharm"* ]] && _pycharm="1" || _pycharm=""
        [[ "$selection" == *"IntelliJ IDEA"* ]] && _idea="1" || _idea=""
        [[ "$selection" == *"WebStorm"* ]] && _wstorm="1" || _wstorm=""
        [[ "$selection" == *"Rider"* ]] && _rider="1" || _rider=""
        [[ "$selection" == *"CLion"* ]] && _clion="1" || _clion=""
        [[ "$selection" == *"RustRover"* ]] && _rustr="1" || _rustr=""
        [[ "$selection" == *"RubyMine"* ]] && _rubym="1" || _rubym=""
        [[ "$selection" == *"DataGrip"* ]] && _datag="1" || _datag=""
        [[ "$selection" == *"PhpStorm"* ]] && _phpstorm="1" || _phpstorm=""
        [[ "$selection" == *"GoLand"* ]] && _goland="1" || _goland=""
        [[ "$selection" == *"Toolbox"* ]] && _tb="1" || _tb=""

        jetbrains_t

    done

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
dsupermenu