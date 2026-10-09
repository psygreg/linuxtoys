#!/bin/bash
# name: ROCm
# version: 1.0
# description: rocm_desc
# icon: amd.png
# reboot: yes
# gpu: ROCm
# compat: !steamos

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# functions
rocm_rpm () {
    if is_rocm_capable; then
        _packages=()
        if is_suse; then
            if [ -n "$suse_leap" ]; then
                sudo zypper --non-interactive addrepo https://download.opensuse.org/repositories/devel:/languages:/perl/$releasever/
                sudo zypper --non-interactive addrepo https://repo.radeon.com/rocm/zyp/latest/main/
                sudo rpm --import https://repo.radeon.com/rocm/rocm.gpg.key
                sudo zypper refresh
                pkg_install rocm clinfo
            else
                sudo zypper ar -f https://download.opensuse.org/repositories/science:/GPU:/ROCm:/Work/openSUSE_Tumbleweed/science:GPU:ROCm:Work.repo
                pkg_install rocm-core rocm-opencl rocm-smi clinfo rocm-hip rocm-llvm rocm-device-libs rocminfo rocm-clang rocm-lld rocm-clinfo
            fi
        else
            pkg_install rocm-comgr rocm-runtime rccl rocalution rocblas rocfft rocm-smi rocsolver rocsparse rocm-device-libs rocminfo rocm-hip hiprand rocm-opencl clinfo
        fi
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_deb () {
    if is_rocm_capable; then
        pkg_install clinfo rocm
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
rocm_arch () {
    if is_rocm_capable; then
        pkg_install rocminfo rocm-opencl-runtime rocm-hip-runtime ocl-icd clinfo
        sudo usermod -aG render,video $USER
    else
        nonfatal "$msg040"
    fi
}
if is_debian || is_ubuntu || is_deepin; then
    sudo_rq
    sudo mkdir --parents --mode=0755 /etc/apt/keyrings
    wget https://repo.radeon.com/rocm/rocm.gpg.key -O - | \
        gpg --dearmor | sudo tee /etc/apt/keyrings/rocm.gpg > /dev/null
    sudo tee /etc/apt/sources.list.d/rocm.list << EOF
deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/7.2.3 noble main
deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/graphics/7.2.3/ubuntu noble main
EOF
    sudo tee /etc/apt/preferences.d/rocm-pin-1001 << EOF
Package: *
Pin: release o=repo.radeon.com
Pin-Priority: 1001
EOF
    sudo apt update
    rocm_deb
elif is_arch || is_cachy; then
    sudo_rq
    rocm_arch
elif is_rhel || is_fedora || is_ostree || is_suse; then
    sudo_rq
    rocm_rpm
elif is_solus; then
    sudo_rq
    pkg_install ocl-icd clinfo rocm-clr rocm-hip rocm-core rocm-llvm rocm-hipify rocminfo rocm-smi rocm-opencl rocfft rocblas rccl hipblas hipsolver hipsparse hipmagma rocsolver rocsparse rocrand rocthrust rocprim
    sudo usermod -aG render,video $USER
else
    fatal "$msg077"
fi
if ! clinfo_chk; then
    fatal "$nocl"
else
    info "$rebootmsg"
fi
