#!/bin/bash
# name: Intel Compute Runtime
# version: 1.0
# description: icr_desc
# icon: intel.png
# reboot: yes
# gpu: Intel

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# function
icr_in () {
    if is_debian || is_ubuntu; then
        pkg_install intel-opencl-icd clinfo
    elif is_suse; then
        pkg_install intel-opencl clinfo
    else
        pkg_install intel-compute-runtime clinfo
    fi
}
if is_intel; then
    sudo_rq
    icr_in
    zeninf "$msg036"
else
    nonfatal "$msg077"
    exit 1
fi