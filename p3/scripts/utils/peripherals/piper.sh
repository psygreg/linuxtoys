#!/bin/bash
# name: Piper
# version: 1.0
# description: piper_desc
# icon: piper.svg
# reboot: yes
# repo: https://github.com/libratbag/piper

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
if is_debian || is_ubuntu; then
    if [[ "$VERSION_ID" =~ "24" ]]; then
        pkg_exists cmake libudev-dev libevdev-dev libsystemd-dev libglib2.0-dev libjson-glib-dev libunistring-dev check valgrind swig ninja-build python3-dev
        pkg_install "${pkg_notfound[@]}"
        prep_tmp_noram
        git clone https://github.com/libratbag/libratbag.git && cd libratbag
        meson builddir --prefix=/usr
        ninja -C builddir
        sudo ninja -C builddir install
        pkg_rm "${pkg_notfound[@]}"
    else
        pkg_install ratbagd
    fi
elif is_arch || is_cachy || is_solus; then
    pkg_install libratbag
elif is_fedora || is_ostree || is_rhel; then
    pkg_install libratbag-ratbagd
elif is_suse; then
    pkg_install libratbag-tools
fi
pkg_flat org.freedesktop.Piper
zeninf "$finishmsg"