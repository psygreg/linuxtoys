#!/bin/bash
# name: RustiCL
# version: 1.0
# description: rusticl_desc
# icon: device.svg
# reboot: yes

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# function
rusticl_in () {
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        _packages=(mesa-opencl-icd clinfo)
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        _packages=(mesa-libOpenCL clinfo)
    elif [[ "$ID_LIKE" == *suse* ]]; then
        _packages=(Mesa-libRusticlOpenCL clinfo)
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        _packages=(opencl-mesa clinfo)
    fi
    _install_
}
amdGPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'amd|ati|radeon|amdgpu')
if [[ -n "$amdGPU" ]]; then
    sudo_rq
    rusticl_in
    curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/rusticl-amd \
        | sudo tee -a /etc/environment > /dev/null
    zeninf $"Reboot your system to apply the changes."
else
    intelGPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'intel')
    if [[ -n "$intelGPU" ]]; then
        sudo_rq
        rusticl_in
        curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/rusticl-intel \
            | sudo tee -a /etc/environment > /dev/null
        zeninf $"Reboot your system to apply the changes."
    else
        nonfatal $"This script is not compatible with your operating system."
        exit 1
    fi
fi