#!/bin/bash
# name: Intel Compute Runtime
# version: 1.0
# description: icr_desc
# icon: intel
# reboot: yes

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
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
    zeninf "$msg036"
else
    nonfatal "$msg077"
    exit 1
fi