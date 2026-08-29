#!/bin/bash
# name: Acer Manager
# version: 1.0
# description: damx_desc
# icon: damx.png
# reboot: yes
# compat: !solus
# repo: https://github.com/PXDiv/Div-Acer-Manager-Max
# revert: internal

source "$SCRIPT_DIR/libs/linuxtoys.lib"

_gh_user="PXDiv"
_gh_repo="Div-Acer-Manager-Max"
_vers="$(
    curl -fsSLI \
        "https://github.com/${_gh_user}/${_gh_repo}/releases/latest" |
        awk -F'/|\r' '/^location:/ {print $(NF-1)}'
)"
_tarb="$(
    curl -fsSL \
        "https://github.com/${_gh_user}/${_gh_repo}/releases/expanded_assets/${_vers}" |
        grep -Pio '(?<=href=")([^"]+\.tar\.xz)' |
        head -n1
)"
[ -n "${_vers}" ] && [ -n "${_tarb}" ] || die "Unable to locate the latest DAMX release"
prep_tmp_noram
mkdir -p damx

curl -fsSL "https://github.com/${_tarb}" -o- |
    tar -xJf - -C damx --strip-components=1 ||
    die "Failed to download or extract DAMX"

if is_debian || is_ubuntu; then
    pkg_install make build-essential
elif is_arch || is_cachy; then
    _k="$(uname -r | grep -o -E 'rt-lts|lts|zen|rt|hardened' | head -n1)"
    pkg_install base-devel "linux${_k:+-${_k}}-headers"
elif is_fedora || is_rhel || is_suse; then
    pkg_install make gcc kernel-headers kernel-devel
fi

cd damx || die "Failed to enter DAMX directory"
sed -i \
    '/Exiting installer\. Goodbye!/{n;s/^[[:space:]]*exit 0[[:space:]]*$/        exit 100 # LinuxToys cancellation/;}' \
    setup.sh

askpass
sudo bash setup.sh
_damx_status=$?
case "${_damx_status}" in
    0|2) info "$rebootmsg" ;;
    100) exit 100 ;;
    *) die "Acer Manager installation unsuccessful" ;;
esac