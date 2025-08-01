#!/bin/bash

# initialize variables for reboot status
flatpak_run=""
# supermenu checklist
usupermenu () {

    local selection
    local selection_str
    local selected
    local search_item
    local item
    declare -a search_item=(
        "GPU Screen Recorder"
        "OBS Studio"
        "HandBrake"
        "Solaar"
        "OpenRazer"
        "OpenRGB"
        "StreamController"
        "Flatseal"
        "Warehouse"
        "Easy Effects"
        "QPWGraph"
        "btrfs-Assistant"
        "LACT"
        "Waydroid"
        "Docker"
        "Rusticl"
        "ROCm"
    )

    while true; do

        selection_str=$(zenity --list --checklist --title="Utilities Menu" \
            --column="" \
            --column="Apps" \
            FALSE "GPU Screen Recorder" \
            FALSE "OBS Studio" \
            FALSE "HandBrake" \
            FALSE "Solaar" \
            FALSE "OpenRazer" \
            FALSE "OpenRGB" \
            FALSE "StreamController" \
            FALSE "Flatseal" \
            FALSE "Warehouse" \
            FALSE "Easy Effects" \
            FALSE "QPWGraph" \
            FALSE "btrfs-Assistant" \
            FALSE "LACT" \
            FALSE "Waydroid" \
            FALSE "Docker" \
            FALSE "Rusticl" \
            FALSE "ROCm" \
            --height=740 --width=360 --separator="|")

        if [ $? -ne 0 ]; then
            break
        fi

        IFS='|' read -ra selection <<< "$selection_str"

        for item in "${search_item[@]}"; do
            for selected in "${selection[@]}"; do
                if [[ "$selected" == "$item" ]]; then
                    case $item in
                        "GPU Screen Recorder") _gsr="com.dec05eba.gpu_screen_recorder" ;;
                        "OBS Studio") _obs="com.obsproject.Studio" ;;
                        "HandBrake") _hndbrk="fr.handbrake.ghb" ;;
                        "Solaar") _slar="solaar" ;;
                        "OpenRazer") _oprzr="openrazer-meta" ;;
                        "OpenRGB") _oprgb="org.openrgb.OpenRGB" ;;
                        "StreamController") _sc="com.core447.StreamController" ;;
                        "Flatseal") _fseal="com.github.tchx84.Flatseal" ;;
                        "Warehouse") _wrhs="io.github.flattool.Warehouse" ;;
                        "Easy Effects") _efx="com.github.wwmm.easyeffects" ;;
                        "QPWGraph") _qpw="org.rncbc.qpwgraph" ;;
                        "btrfs-Assistant") _btassist="btrfs-assistant" ;;
                        "LACT") _lact="io.github.ilya_zlobintsev.LACT" ;;
                        "Waydroid") _droid="waydroid" ;;
                        "Docker") _dckr="yes" ;;
                        "Rusticl") _rcl="yes" ;;
                        "ROCm") _rocm="yes" ;;
                    esac
                fi
            done
        done

        install_flatpak
        install_native
        if [[ -n "$flatpak_run" || -n "$_oprzr" || -n "$_rocm" ]]; then
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

    local _bt_package=""
    local _wd_package=""
    if [[ -n "$_btassist" ]]; then
        if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
            _bt_package=($_btassist)
        else
            nonfatal "$msg220"
        fi
    fi
    if [[ -n "$_droid" ]]; then
        if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
            _wd_package=($_droid)
        else
            nonfatal "$msg219"
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
                if zenity --question --text "$msg035" --width 360 --height 300; then
                    chaotic_aur_lib
                else
                    zenwrn "Skipping btrfs-assistant installation."
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
                nonfatal "$msg097"
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

    zenwrn "$msg098"
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
        nonfatal "$msg040"
    fi

}

rocm_deb () {

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local _packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi

}

rocm_arch () { 

    local GPU=$(lspci | grep -i 'radeon .*')
    if [[ -n "$GPU" ]]; then
        local _packages=(comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi-lib rocminfo hipcc hiprand hip-runtime-amd radeontop rocm-opencl-runtime ocl-icd clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi

}

# flatpak packages
install_flatpak () {

    local _flatpaks=($_gsr $_obs $_hndbrk $_lact $_oprgb $_fseal $_sc $_qpw $_wrhs)
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
            if zenity --question --text "$msg085" --width 360 --height 300; then
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
                nonfatal "$msg132"
            fi
        fi
    fi

}

# runtime
. /etc/os-release
source linuxtoys.lib
_lang_
source ${langfile}
usupermenu
