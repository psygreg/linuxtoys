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
usupermenu () {

    local gsr_status=$([ "$_gsr" = "com.dec05eba.gpu_screen_recorder" ] && echo "ON" || echo "OFF")
    local obs_status=$([ "$_obs" = "obs-studio" ] && echo "ON" || echo "OFF")
    local hndbrk_status=$([ "$_hndbrk" = "fr.handbrake.ghb" ] && echo "ON" || echo "OFF")
    local slar_status=$([ "$_slar" = "solaar" ] && echo "ON" || echo "OFF")
    local oprzr_status=$([ "$_oprzr" = "openrazer" ] && echo "ON" || echo "OFF")
    local oprgb_status=$([ "$_oprgb" = "org.openrgb.OpenRGB" ] && echo "ON" || echo "OFF")
    local btassist_status=$([ "$_btassist" = "btrfs-assistant" ] && echo "ON" || echo "OFF")
    local lact_status=$([ "$_lact" = "io.github.ilya_zlobintsev.LACT" ] && echo "ON" || echo "OFF")
    local droid_status=$([ "$_droid" = "waydroid" ] && echo "ON" || echo "OFF")
    local dckr_status=$([ "$_dckr" = "yes" ] && echo "ON" || echo "OFF")
    local rocm_status=$([ "$_rocm" = "yes" ] && echo "ON" || echo "OFF")
    local fseal_status=$([ "$_fseal" = "com.github.tchx84.Flatseal" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "GPU Screen Recorder" "$msg086" $gsr_status \
            "OBS Studio" "Open Broadcaster Software" $obs_status \
            "HandBrake" "$msg087" $hndbrk_status \
            "Solaar" "$msg088" $slar_status \
            "OpenRazer" "$msg089" $oprzr_status \
            "OpenRGB" "$msg091" $oprgb_status \
            "Flatseal" "$msg133" $fseal_status \
            "btrfs-Assistant" "$msg092" $btassist_status \
            "LACT" "$msg093" $lact_status \
            "Waydroid" "$msg094" $droid_status \
            "Docker" "$msg095" $dckr_status \
            "ROCm" "$msg096" $rocm_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"GPU Screen Recorder"* ]] && _gsr="com.dec05eba.gpu_screen_recorder" || _gsr=""
        [[ "$selection" == *"OBS Studio"* ]] && _obs="obs-studio" || _obs=""
        [[ "$selection" == *"HandBrake"* ]] && _hndbrk="fr.handbrake.ghb" || _hndbrk=""
        [[ "$selection" == *"Solaar"* ]] && _slar="solaar" || _slar=""
        [[ "$selection" == *"OpenRazer"* ]] && _oprzr="openrazer" || _oprzr=""
        [[ "$selection" == *"OpenRGB"* ]] && _oprgb="org.openrgb.OpenRGB" || _oprgb=""
        [[ "$selection" == *"btrfs-Assistant"* ]] && _btassist="btrfs-assistant" || _btassist=""
        [[ "$selection" == *"LACT"* ]] && _lact="io.github.ilya_zlobintsev.LACT" || _lact=""
        [[ "$selection" == *"Waydroid"* ]] && _droid="waydroid" || _droid=""
        [[ "$selection" == *"Docker"* ]] && _dckr="yes" || _dckr=""
        [[ "$selection" == *"ROCm"* ]] && _rocm="yes" || _rocm=""
        [[ "$selection" == *"Flatseal"* ]] && _fseal="com.github.tchx84.Flatseal" || _fseal=""

        install_flatpak
        install_native
        if [[ -n "$flatpak_run" || -n "$_oprzr" || -n "$_rocm" ]]; then
            whiptail --title "$msg006" --msgbox "$msg036" 8 78
        else
            whiptail --title "$msg006" --msgbox "$msg018" 8 78
        fi
    
    done

}

# installer functions
# native packages
install_native () {

    if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
        local _packages=($_obs $_slar $_oprzr $_btassist $_droid $_dckr)
    else
        local _packages=($_obs $_slar $_oprzr $_droid $_dckr)
    fi
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            if [[ "$ID_LIKE" =~ (ubuntu|debian) ]]; then
                if [[ -n "$_slar" ]]; then
                    sudo add-apt-repository ppa:solaar-unifying/stable
                    sudo apt update
                fi
            fi
            if [[ -n "$_droid" ]]; then
                sudo apt install curl ca-certificates -y
                curl -s https://repo.waydro.id | sudo bash
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_deb
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" == "yes" ]]; then
                    continue
                fi
                sudo apt install -y $pak
            done
            if [[ -n "$_obs" ]]; then
                if dpkg -s "pipewire" 2>/dev/null 1>&2; then
                    obs_pipe
                fi
            fi
        elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
            if [[ -n "$_btassist" ]]; then
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
                else
                    whiptail --title "$msg006" --msgbox "Skipping btrfs-assistant installation." 8 78
                fi
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_arch
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (openrazer|yes) ]]; then
                    sudo pacman -S --noconfirm openrazer-daemon
                fi
                sudo pacman -S --noconfirm $pak
            done
            if [[ -n "$_obs" ]]; then
                if pacman -Qi "pipewire" 2>/dev/null 1>&2; then
                    obs_pipe
                fi
            fi
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [[ -n "$_oprzr" ]]; then
                sudo dnf in kernel-devel -y
                sudo dnf config-manager addrepo --from-repofile=https://openrazer.github.io/hardware:razer.repo
                sudo dnf in openrazer-meta -y
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_rpm
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (openrazer|yes) ]]; then
                    continue
                fi
                sudo dnf in $pak -y
            done
            if [[ -n "$_obs" ]]; then
                if rpm -qi "pipewire" 2>/dev/null 1>&2; then
                    obs_pipe
                fi
            fi
        elif [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            if [[ -n "$_oprzr" ]]; then
                if grep -qi "slowroll" /etc/os-release; then
                    sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Slowroll/hardware:razer.repo
                else
                    sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Tumbleweed/hardware:razer.repo
                fi
                sudo zypper refresh
                sudo zypper in openrazer-meta -y
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_rpm
            fi
            if [[ -n "$_droid" ]]; then
                whiptail --title "Waydroid" --msgbox "$msg097" 12 78
            fi
            for pak in "${_packages[@]}"; do
                if [[ "$pak" =~ (openrazer|yes|waydroid) ]]; then
                    continue
                fi
                sudo zypper in $pak -y
            done
            if [[ -n "$_obs" ]]; then
                if rpm -qi "pipewire" 2>/dev/null 1>&2; then
                    obs_pipe
                fi
            fi
        fi
    fi

}

# obs pipewire audio capture plugin installation
obs_pipe () {

    whiptail --title "$msg006" --msgbox "$msg098" 8 78
    cd $HOME
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/pipewire-obs.sh
    chmod +x pipewire-obs.sh
    ./pipewire-obs.sh
    rm pipewire-obs.sh

}

# docker + portainer CE setup
docker_t () {

    cd $HOME
    wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/docker-installer.sh
    chmod +x docker-installer.sh
    ./docker-installer.sh
    rm docker-installer.sh

}

# ROCm installer setups
rocm_rpm () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local packages=()
        if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
            packages=(libamd_comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas4 librocfft0 librocm_smi64_1 librocsolver0 librocsparse1 rocm-device-libs rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl ocl-icd clinfo)
        else
            packages=(rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand hiprtc radeontop rocm-opencl ocl-icd clinfo)
        fi
        for pac in "${packages[@]}"; do
            if rpm -qi "$pac" 2>/dev/null 1>&2; then
                continue
            else
                if [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ]; then
                    sudo zypper in "$pac" -y
                else
                    sudo dnf in "$pac" -y
                fi
            fi
        done
        sudo usermod -aG render,video $USER
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
    fi

}

rocm_deb () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
        for pac in "${packages[@]}"; do
            if dpkg -s "$pac" 2>/dev/null 1>&2; then
                continue
            else
                sudo apt install -y "$pac"
            fi
        done
        sudo usermod -aG render,video $USER
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
    fi

}

rocm_arch () { 

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local packages=(amd-comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi rocminfo hipcc hiprand hiprtc radeontop rocm-opencl-runtime ocl-icd clinfo)
        for pac in "${packages[@]}"; do
            if pacman -Qi "$pac" 2>/dev/null 1>&2; then 
                continue
            else
                sudo pacman -S --noconfirm "$pac"
            fi
        done
        sudo usermod -aG render,video $USER
    else
        whiptail --title "$msg039" --msgbox "$msg040" 8 78
    fi

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_hndbrk $_lact $_gsr $_oprgb $_fseal)
    if [[ -n "$_flatpaks" ]]; then
        if command -v flatpak &> /dev/null; then
            for flat in "${_flatpaks[@]}"; do
                flatpak install --or-update -y $flat --system
            done
            if [[ -n "$_hndbrk" ]]; then
                if lspci | grep -iE 'vga|3d' | grep -iq 'intel'; then
                    flatpak install --or-update -y fr.handbrake.ghb.Plugin.IntelMediaSDK --system
                fi
            fi
            if [[ -n "$_oprgb" ]]; then
                cd $HOME
                wget https://openrgb.org/releases/release_0.9/60-openrgb.rules
                sudo cp 60-openrgb.rules /usr/lib/udev/rules.d/
                sudo udevadm control --reload-rules && sudo udevadm trigger
            fi
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
                    sudo apt install -y flatpak
                    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
                    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
                    for flat in "${_flatpaks[@]}"; do
                        flatpak install --or-update -y $flat --system
                    done
                    if [[ -n "$_hndbrk" ]]; then
                        if lspci | grep -iE 'vga|3d' | grep -iq 'intel'; then
                            flatpak install --or-update -y fr.handbrake.ghb.Plugin.IntelMediaSDK --system
                        fi
                    fi
                    if [[ -n "$_oprgb" ]]; then
                        cd $HOME
                        wget https://openrgb.org/releases/release_0.9/60-openrgb.rules
                        sudo cp 60-openrgb.rules /usr/lib/udev/rules.d/
                        sudo udevadm control --reload-rules && sudo udevadm trigger
                    fi
                elif [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
                    sudo pacman -S --noconfirm flatpak
                    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
                    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
                    for flat in "${_flatpaks[@]}"; do
                        flatpak install --or-update -y $flat --system
                    done
                    if [[ -n "$_hndbrk" ]]; then
                        if lspci | grep -iE 'vga|3d' | grep -iq 'intel'; then
                            flatpak install --or-update -y fr.handbrake.ghb.Plugin.IntelMediaSDK --system
                        fi
                    fi
                    if [[ -n "$_oprgb" ]]; then
                        cd $HOME
                        wget https://openrgb.org/releases/release_0.9/60-openrgb.rules
                        sudo cp 60-openrgb.rules /usr/lib/udev/rules.d/
                        sudo udevadm control --reload-rules && sudo udevadm trigger
                    fi
                fi
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
usupermenu