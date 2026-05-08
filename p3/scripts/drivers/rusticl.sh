#!/bin/bash
# name: RustiCL
# version: 1.0
# description: rusticl_desc
# icon: device.svg
# reboot: yes
# gpu: Amd, Intel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# function
rusticl_in () {
    if is_debian || is_ubuntu; then
        pkg_install mesa-opencl-icd clinfo
    elif is_fedora; then
        pkg_install mesa-libOpenCL clinfo
    elif is_suse; then
        pkg_install Mesa-libRusticlOpenCL clinfo
    elif is_arch || is_cachy; then
        pkg_install opencl-mesa clinfo
    elif is_solus; then
        pkg_install ocl-icd clinfo
    fi
}
if is_amd; then
    sudo_rq
    rusticl_in
    prep_edit /etc/environment
    curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/rusticl-amd \
        | sudo tee -a /etc/environment > /dev/null
    zeninf "$msg036"
else
    if is_intel; then
        sudo_rq
        rusticl_in
        prep_edit /etc/environment
        curl -sL https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/rusticl-intel \
            | sudo tee -a /etc/environment > /dev/null
        zeninf "$msg036"
    else
        nonfatal "$msg077"
        exit 1
    fi
fi
