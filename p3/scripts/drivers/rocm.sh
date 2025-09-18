#!/bin/bash
# name: ROCm
# version: 1.0
# description: rocm_desc
# icon: amd.png
# reboot: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# functions
rocm_rpm () {
    local GPU=$(lspci | grep -Ei '(radeon|rx)')
    if [[ -n "$GPU" ]]; then
        _packages=()
        if [[ "$ID_LIKE" == *suse* ]]; then
            _packages=(libamd_comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas4 librocfft0 librocm_smi64_1 librocsolver0 librocsparse1 rocm-device-libs rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl ocl-icd clinfo)
        else
            _packages=(rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo)
        fi
        _install_
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_deb () {
    local GPU=$(lspci | grep -Ei '(radeon|rx)')
    if [[ -n "$GPU" ]]; then
        _packages=(libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_arch () {
    local GPU=$(lspci | grep -Ei '(radeon|rx)')
    if [[ -n "$GPU" ]]; then
        _packages=(comgr hsa-rocr rccl rocalution rocblas rocfft rocm-smi-lib rocsolver rocsparse rocm-device-libs rocm-smi-lib rocminfo hipcc hiprand hip-runtime-amd radeontop rocm-opencl-runtime ocl-icd clinfo)
        _install_
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    sudo_rq
    rocm_deb
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    sudo_rq
    rocm_arch
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ] || [ "$ID" == "suse" ] || [[ "$ID_LIKE" == *suse* ]]; then
    sudo_rq
    rocm_rpm
fi