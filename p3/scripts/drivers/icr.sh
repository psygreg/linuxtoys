#!/bin/bash
# name: Intel Compute Runtime
# version: 1.0
# description: icr_desc
# icon: intel.png
# reboot: yes

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# function
icr_in () {
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        _packages=(intel-compute-runtime)
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        _packages=(intel-compute-runtime)
    elif [[ "$ID_LIKE" == *suse* ]] || [[ "$ID_LIKE" == *opensuse* ]] || [[ "$ID" =~ "suse" ]]; then
        _packages=(intel-opencl)
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        _packages=(intel-compute-runtime)
    fi
    _install_
}
intelGPU=$(lspci | grep -Ei 'vga|3d' | grep -Ei 'intel')
if [[ -n "$intelGPU" ]]; then
    sudo_rq
    icr_in
    zeninf $"Reboot your system to apply the changes."
else
    nonfatal $"This script is not compatible with your operating system."
    exit 1
fi