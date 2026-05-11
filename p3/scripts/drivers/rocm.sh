#!/bin/bash
# name: ROCm
# version: 1.0
# description: rocm_desc
# icon: amd.png
# reboot: yes
# gpu: AMD

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# functions
rocm_rpm () {
    if is_amd; then
        _packages=()
        if [[ "$ID_LIKE" == *suse* ]]; then
            pkg_install libamd_comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas4 librocfft0 librocm_smi64_1 librocsolver0 librocsparse1 rocm-device-libs rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl ocl-icd clinfo
        else
            pkg_install rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo
        fi
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_deb () {
    if is_amd; then
        pkg_install clinfo rocm
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_arch () {
    if is_amd; then
        pkg_install rocminfo rocm-opencl-runtime rocm-hip-runtime ocl-icd clinfo
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    sudo_rq
    sudo mkdir --parents --mode=0755 /etc/apt/keyrings
    wget https://repo.radeon.com/rocm/rocm.gpg.key -O - | \
        gpg --dearmor | sudo tee /etc/apt/keyrings/rocm.gpg > /dev/null
    sudo tee /etc/apt/sources.list.d/rocm.list << EOF
deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/7.2.3 noble main
deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/graphics/7.2.3/ubuntu noble main
EOF
    sudo tee /etc/apt/preferences.d/rocm-pin-600 << EOF
Package: *
Pin: release o=repo.radeon.com
Pin-Priority: 600
EOF
    sudo apt update
    rocm_deb
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    sudo_rq
    rocm_arch
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ] || [ "$ID" == "suse" ] || [[ "$ID_LIKE" == *suse* ]]; then
    sudo_rq
    rocm_rpm
elif is_solus; then
    sudo_rq
    pkg_install ocl-icd clinfo rocm-clr rocm-hip rocm-core rocm-llvm rocm-hipify rocminfo rocm-smi rocm-opencl rocfft rocblas rccl hipblas hipsolver hipsparse hipmagma rocsolver rocsparse rocrand rocthrust rocprim
    sudo usermod -aG render,video $USER
else
    fatal "$msg077"
fi