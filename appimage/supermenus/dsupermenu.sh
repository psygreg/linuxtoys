#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
dsupermenu () {

    local selection_str
    local selected
    local selection
    local search_item
    local item
    declare -a search_item=(
        "VS Code"
        "VSCodium"
        "NeoVim"
        "Jetbrains - ${msg162}"
        "OhMyBash"
        "NodeJS + NVM"
        "Maven"
        "Python + Pyenv"
        "C# - .NET SDK"
        "Java - OpenJDK/JRE"
        "Android Studio"
        "Godot 4"
        "Unity Hub"
        "Insomnia"
        "Httpie"
        "Postman"
    )

    while true; do

        selection_str=$(zenity --list --checklist --title="Developer Menu" \
            --column="" \
            --column="Apps" \
            FALSE "VS Code" \
            FALSE "VSCodium" \
            FALSE "NeoVim" \
            FALSE "Jetbrains - ${msg162}" \
            FALSE "OhMyBash" \
            FALSE "NodeJS + NVM" \
            FALSE "Maven" \
            FALSE "Python + Pyenv" \
            FALSE "C# - .NET SDK" \
            FALSE "Java - OpenJDK/JRE"\
            FALSE "Android Studio" \
            FALSE "Godot 4" \
            FALSE "Unity Hub" \
            FALSE "Insomnia" \
            FALSE "Httpie" \
            FALSE "Postman" \
            --height=730 --width=360 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra selection <<< "$selection_str"

        for item in "${search_item[@]}"; do
            for selected in "${selection[@]}"; do
                if [[ "$selected" == "$item" ]]; then
                    # if item is found, set the corresponding variable
                    case $item in
                        "VS Code") _code="code" ;;
                        "VSCodium") _codium="com.vscodium.codium" ;;
                        "NeoVim") _nvim="neovim" ;;
                        "Jetbrains - ${msg162}") _jb="1" ;;
                        "OhMyBash") _omb="1" ;;
                        "NodeJS + NVM") _nvm="nodejs" ;;
                        "Maven") _mvn="maven" ;;
                        "Python + Pyenv") _pyenv="pyenv" ;;
                        "C# - .NET SDK") _dotnet="dotnet-sdk-9.0" ;;
                        "Java - OpenJDK/JRE") _java="java" ;;
                        "Android Studio") _droidstd="droidstd" ;;
                        "Godot 4") _godot="godot" ;;
                        "Unity Hub") _unity="unityhub" ;;
                        "Insomnia") _insomnia="rest.insomnia.Insomnia" ;;
                        "Httpie") _httpie="io.httpie.Httpie" ;;
                        "Postman") _postman="com.getpostman.Postman" ;;
                    esac
                fi
            done
        done

        install_flatpak
        install_native
        others_t
        # adjust if rebooting is required for any software
        if [[ -n "$flatpak_run" || -n "$_pyenv" || -n "$_nvm" ]]; then
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
                if zenity --question --text "$msg035" --width 360 --height 300; then
                    chaotic_aur_lib
                    insta visual-studio-code-bin
                else
                    zenwrn "Skipping Visual Studio Code installation."
                fi
            fi
            if [[ -n "$_pyenv" ]]; then
                insta base-devel openssl zlib xz tk
            fi
            if [[ -n "$_unity" ]]; then
                nonfatal "$msg077"
            fi
            if [[ -n "$_dotnet" ]]; then
                nonfatal "$msg077"
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
                    nonfatal "$msg077"
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
                    nonfatal "$msg077"
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
            if zenity --question --text "$msg085" --width 360 --height 300; then
                flatpak_run="1"
                flatpak_in_lib
                _flatpak_
            else
                nonfatal "$msg132"
            fi
        fi
    fi

}

# Godot Engine installer
godot_in () {

    # menu
    while :; do

        CHOICE=$(zenity --list --title "Godot Engine" --text "$msg067" \
            --column "Options" \
            "Godot (Default)" \
            "Godot .NET (C# Support)" \
            "Cancel" \
            --width 300 --height 330)

        if [ $? -ne 0 ]; then
            exit 0
        fi

        case $CHOICE in
        "Godot (Default)") godot_st ;;
        "Godot .NET (C# Support)") godot_shrp ;;
        "Cancel") break ;;
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
        nonfatal "$msg077"

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

    local search_java
    local jav
    local chosen_javas
    local chosen_jav
    local javas
    declare -a search_java=(
        "Java 8 LTS"
        "Java 11 LTS"
        "Java 17 LTS"
        "Java 21 LTS"
        "Java 24 Latest"
    )

    while true; do

        chosen_javas=$(zenity --list --checklist --title="Java JDK" \
        	--column="" \
        	--column="$msg277" \
            FALSE "Java 8 LTS" \
            FALSE "Java 11 LTS" \
            FALSE "Java 17 LTS" \
            FALSE "Java 21 LTS" \
            FALSE "Java 24 Latest" \
            --height=410 --width=300 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra javas <<< "$chosen_javas"

        for jav in "${search_java[@]}"; do
            for chosen_jav in "${javas[@]}"; do
                if [[ "$chosen_jav" == "$jav" ]]; then
                    case $jav in
                        "Java 8 LTS") _jdk8="8" ;;
                        "Java 11 LTS") _jdk11="11" ;;
                        "Java 17 LTS") _jdk17="17" ;;
                        "Java 21 LTS") _jdk21="21" ;;
                        "Java 24 Latest") _jdk24="24" ;;
                    esac
                fi
            done
        done

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
        zeninf "$msg136"
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
        zeninf "$msg135"
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
    while true; do

        CHOICE=$(zenity --list --title "IntelliJ IDEA" --text "$msg067" \
            --column "Options" \
            "Community Edition (free)" \
            "Ultimate" \
            "Cancel" \
            --width 300 --height 330)

        if [ $? -ne 0 ]; then
            exit 0
        fi

        case $CHOICE in
        "Community Edition (free)") idea_ic && return ;;
        "Ultimate") idea_iu && return ;;
        "Cancel") return ;;
        *) echo "Invalid Option" ;;
        esac
    done

}

# jetbrains trigger
jetbrains_t () {

    if [[ -n "$_tb" ]]; then
        if zenity --question --text "$msg173" --width 360 --height 300; then
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

    local selection_str
    local selected
    local selection
    local search_item
    declare -a search_item=(
        "PyCharm"
        "IntelliJ IDEA"
        "WebStorm"
        "Rider"
        "CLion"
        "RustRover"
        "RubyMine"
        "DataGrip"
        "PhpStorm"
        "GoLand"
        "Toolbox"
    )

    while true; do

        selection_str=$(zenity --list --checklist --title="$msg131" \
            --column="" \
            --column="Apps" \
            FALSE "PyCharm" \
            FALSE "IntelliJ IDEA" \
            FALSE "WebStorm" \
            FALSE "Rider" \
            FALSE "CLion" \
            FALSE "RustRover" \
            FALSE "RubyMine" \
            FALSE "DataGrip" \
            FALSE "PhpStorm" \
            FALSE "GoLand" \
            FALSE "Toolbox" \
            --height=620 --width=300 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra selection <<< "$selection_str"

        for item in "${search_item[@]}"; do
            for selected in "${selection[@]}"; do
                if [[ "$selected" == "$item" ]]; then
                    # if item is found, set the corresponding variable
                    case $item in
                        "PyCharm") _pycharm="1" ;;
                        "IntelliJ IDEA") _idea="1" ;;
                        "WebStorm") _wstorm="1" ;;
                        "Rider") _rider="1" ;;
                        "CLion") _clion="1" ;;
                        "RustRover") _rustr="1" ;;
                        "RubyMine") _rubym="1" ;;
                        "DataGrip") _datag="1" ;;
                        "PhpStorm") _phpstorm="1" ;;
                        "GoLand") _goland="1" ;;
                        "Toolbox") _tb="1" ;;
                    esac
                fi
            done
        done

        jetbrains_t

    done

}

# runtime
. /etc/os-release
source linuxtoys.lib
_lang_
source ${langfile}
dsupermenu
