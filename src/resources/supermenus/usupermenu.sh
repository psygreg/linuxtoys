#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
usupermenu () {

    local gsr_status=$([ "$_gsr" = "com.dec05eba.gpu_screen_recorder" ] && echo "ON" || echo "OFF")
    local obs_status=$([ "$_obs" = "com.obsproject.Studio" ] && echo "ON" || echo "OFF")
    local hndbrk_status=$([ "$_hndbrk" = "fr.handbrake.ghb" ] && echo "ON" || echo "OFF")
    local slar_status=$([ "$_slar" = "solaar" ] && echo "ON" || echo "OFF")
    local oprzr_status=$([ "$_oprzr" = "openrazer-meta" ] && echo "ON" || echo "OFF")
    local oprgb_status=$([ "$_oprgb" = "org.openrgb.OpenRGB" ] && echo "ON" || echo "OFF")
    local btassist_status=$([ "$_btassist" = "btrfs-assistant" ] && echo "ON" || echo "OFF")
    local lact_status=$([ "$_lact" = "io.github.ilya_zlobintsev.LACT" ] && echo "ON" || echo "OFF")
    local droid_status=$([ "$_droid" = "waydroid" ] && echo "ON" || echo "OFF")
    local dckr_status=$([ "$_dckr" = "yes" ] && echo "ON" || echo "OFF")
    local rocm_status=$([ "$_rocm" = "yes" ] && echo "ON" || echo "OFF")
    local rcl_status=$([ "$_rcl" = "yes" ] && echo "ON" || echo "OFF")
    local fseal_status=$([ "$_fseal" = "com.github.tchx84.Flatseal" ] && echo "ON" || echo "OFF")
    local efx_status=$([ "$_efx" = "com.github.wwmm.easyeffects" ] && echo "ON" || echo "OFF")
    local sc_status=$([ "$_sc" = "com.core447.StreamController" ] && echo "ON" || echo "OFF")
    local qpw_status=$([ "$_qpw" = "org.rncbc.qpwgraph" ] && echo "ON" || echo "OFF")
    local wrhs_status=$([ "$_wrhs" = "io.github.flattool.Warehouse" ] && echo "ON" || echo "OFF")

    while :; do

        local selection
        selection=$(whiptail --title "$msg131" --checklist \
            "$msg131" 20 78 15 \
            "GPU Screen Recorder" "$msg086" $gsr_status \
            "OBS Studio" "Open Broadcaster Software" $obs_status \
            "HandBrake" "$msg087" $hndbrk_status \
            "Solaar" "$msg088" $slar_status \
            "OpenRazer" "$msg089" $oprzr_status \
            "StreamController" "$msg151" $sc_status \
            "OpenRGB" "$msg091" $oprgb_status \
            "Flatseal" "$msg133" $fseal_status \
            "Warehouse" "$msg218" $wrhs_status \
            "Easy Effects" "$msg147" $efx_status \
            "QPWGraph" "$msg179" $qpw_status \
            "btrfs-Assistant" "$msg092" $btassist_status \
            "LACT" "$msg093" $lact_status \
            "Waydroid" "$msg094" $droid_status \
            "Docker" "$msg095" $dckr_status \
            "Rusticl" "$msg158" $rcl_status \
            "ROCm" "$msg096" $rocm_status \
            3>&1 1>&2 2>&3)

        exitstatus=$?
        if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
            break
        fi

        [[ "$selection" == *"GPU Screen Recorder"* ]] && _gsr="com.dec05eba.gpu_screen_recorder" || _gsr=""
        [[ "$selection" == *"OBS Studio"* ]] && _obs="com.obsproject.Studio" || _obs=""
        [[ "$selection" == *"HandBrake"* ]] && _hndbrk="fr.handbrake.ghb" || _hndbrk=""
        [[ "$selection" == *"Solaar"* ]] && _slar="solaar" || _slar=""
        [[ "$selection" == *"OpenRazer"* ]] && _oprzr="openrazer-meta" || _oprzr=""
        [[ "$selection" == *"OpenRGB"* ]] && _oprgb="org.openrgb.OpenRGB" || _oprgb=""
        [[ "$selection" == *"btrfs-Assistant"* ]] && _btassist="btrfs-assistant" || _btassist=""
        [[ "$selection" == *"LACT"* ]] && _lact="io.github.ilya_zlobintsev.LACT" || _lact=""
        [[ "$selection" == *"Waydroid"* ]] && _droid="waydroid" || _droid=""
        [[ "$selection" == *"Docker"* ]] && _dckr="yes" || _dckr=""
        [[ "$selection" == *"ROCm"* ]] && _rocm="yes" || _rocm=""
        [[ "$selection" == *"Rusticl"* ]] && _rcl="yes" || _rcl=""
        [[ "$selection" == *"Flatseal"* ]] && _fseal="com.github.tchx84.Flatseal" || _fseal=""
        [[ "$selection" == *"Easy Effects"* ]] && _efx="com.github.wwmm.easyeffects" || _efx=""
        [[ "$selection" == *"StreamController"* ]] && _sc="com.core447.StreamController" || _sc=""
        [[ "$selection" == *"QPWGraph"* ]] && _qpw="org.rncbc.qpwgraph" || _qpw=""
        [[ "$selection" == *"Warehouse"* ]] && _wrhs="io.github.flattool.Warehouse" || _wrhs=""

        install_flatpak
        install_native
        if [[ -n "$flatpak_run" || -n "$_oprzr" || -n "$_rocm" ]]; then
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

    local _bt_package=""
    local _wd_package=""
    if [[ -n "$_btassist" ]]; then
        if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
            _bt_package=($_btassist)
        else
            local title="btrfs-Assistant"
            local msg="$msg220"
            _msgbox_
        fi
    fi
    if [[ -n "$_droid" ]]; then
        if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
            _wd_package=($_droid)
        else
            local title="Waydroid"
            local msg="$msg219"
            _msgbox_
        fi
    fi
    local _packages=($_slar $_oprzr $_droid $_dckr $_rocm $_wd_package $_bt_package)
    if [[ -n "$_packages" ]]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            if [ "$ID" == "ubuntu" ]; then
                if [[ -n "$_slar" ]]; then
                    sudo add-apt-repository ppa:solaar-unifying/stable
                    sudo apt update
                fi
                if [[ -n "$_oprzr" ]]; then
                    sudo add-apt-repository ppa:openrazer/stable
                    sudo apt update
                fi
            fi
            if [[ -n "$_droid" ]]; then
                insta curl ca-certificates -y
                curl -s https://repo.waydro.id | sudo bash
                sleep 1
                sudo systemctl enable --now waydroid-container
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_deb
            fi
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            if [[ -n "$_btassist" ]]; then
                if whiptail --title "$msg006" --yesno "$msg035" 8 78; then
                    chaotic_aur_lib
                else
                    local title="$msg006"
                    local msg="Skipping btrfs-assistant installation."
                    _msgbox_
                fi
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_arch
            fi
            if [[ -n "$_droid" ]]; then
                sudo systemctl enable --now waydroid-container
            fi
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            if [[ -n "$_oprzr" ]]; then
                insta kernel-devel -y
                sudo dnf config-manager addrepo --from-repofile=https://openrazer.github.io/hardware:razer.repo
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_rpm
            fi
            if [[ -n "$_droid" ]]; then
                sudo systemctl enable --now waydroid-container
            fi
        elif [[ "$ID_LIKE" == *suse* ]]; then
            if [[ -n "$_oprzr" ]]; then
                if grep -qi "slowroll" /etc/os-release; then
                    sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Slowroll/hardware:razer.repo
                else
                    sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Tumbleweed/hardware:razer.repo
                fi
                sudo zypper refresh
            fi
            if [[ -n "$_dckr" ]]; then
                docker_t
            fi
            if [[ -n "$_rocm" ]]; then
                rocm_rpm
            fi
            if [[ -n "$_droid" ]]; then
                local title="Waydroid"
                local msg="$msg097"
                _msgbox_
            fi
        fi
    fi
    _install_

}

# rusticl installation
rusticl_in () {

    if [[ -n "$_rcl" ]]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            insta mesa-opencl-icd clinfo
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
            insta mesa-libOpenCL clinfo
        elif [[ "$ID_LIKE" == *suse* ]]; then
            insta Mesa-libRusticlOpenCL clinfo
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            insta opencl-mesa clinfo
        fi
        local GPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'amd|ati|radeon|amdgpu')
        if [[ -n "$GPU" ]]; then
            curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/main/src/resources/subscripts/rusticl-amd \
                | sudo tee -a /etc/environment > /dev/null
        else
            local GPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'intel')
            if [[ -n "$GPU" ]]; then
                curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/main/src/resources/subscripts/rusticl-intel \
                    | sudo tee -a /etc/environment > /dev/null
            fi
        fi
    fi

}

# obs pipewire audio capture plugin installation
obs_pipe () {

    local title="$msg006"
    local msg="$msg098"
    _msgbox_
    local subscript="pipewire-obs"
    _invoke_

}

# docker + portainer CE setup
docker_t () {

    cd $HOME
    local subscript="docker-installer"
    _invoke_

}

# ROCm installer setups
rocm_rpm () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local _packages=()
        if [[ "$ID_LIKE" == *suse* ]]; then
            _packages=(libamd_comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas4 librocfft0 librocm_smi64_1 librocsolver0 librocsparse1 rocm-device-libs rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl ocl-icd clinfo)
        else
            _packages=(rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand hiprtc radeontop rocm-opencl ocl-icd clinfo)
        fi
        _install_
        sudo usermod -aG render,video $USER
    else
        local title="$msg039"
        local msg="$msg040"
        _msgbox_
    fi

}

rocm_deb () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local _packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        local title="$msg039"
        local msg="$msg040"
        _msgbox_
    fi

}

rocm_arch () { 

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local _packages=(comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi-lib rocminfo hipcc hiprand hip-runtime-amd radeontop rocm-opencl-runtime ocl-icd clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        local title="$msg039"
        local msg="$msg040"
        _msgbox_
    fi

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_obs $_hndbrk $_lact $_oprgb $_fseal $_sc $_qpw $_wrhs)
    if [[ -n "$_flatpaks" ]]; then
        if command -v flatpak &> /dev/null; then
            flatpak_in_lib
            _flatpak_
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
            if [[ -n "$_efx" ]] && ( rpm -qi "pipewire" 2>/dev/null 1>&2 || pacman -Qi "pipewire" 2>/dev/null 1>&2 || dpkg -s "pipewire" 2>/dev/null 1>&2 ); then
                flatpak install --or-update -y $_efx --system
            fi
            if [[ -n "$_gsr" ]]; then
                flatpak install --or-update -y $_gsr --system
            fi
            if [[ -n "$_obs" ]] && ( rpm -qi "pipewire" 2>/dev/null 1>&2 || pacman -Qi "pipewire" 2>/dev/null 1>&2 || dpkg -s "pipewire" 2>/dev/null 1>&2 ); then
                obs_pipe
            fi
        else
            if whiptail --title "$msg006" --yesno "$msg085" 8 78; then
                flatpak_run="1"
                flatpak_in_lib
                _flatpak_
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
                if [[ -n "$_efx" ]] && ( rpm -qi "pipewire" 2>/dev/null 1>&2 || pacman -Qi "pipewire" 2>/dev/null 1>&2 || dpkg -s "pipewire" 2>/dev/null 1>&2 ); then
                    flatpak install --or-update -y $_efx --system
                fi
                if [[ -n "$_gsr" ]]; then
                    flatpak install --or-update -y $_gsr --system
                fi
                if [[ -n "$_obs" ]] && ( rpm -qi "pipewire" 2>/dev/null 1>&2 || pacman -Qi "pipewire" 2>/dev/null 1>&2 || dpkg -s "pipewire" 2>/dev/null 1>&2 ); then
                    obs_pipe
                fi
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
usupermenu
