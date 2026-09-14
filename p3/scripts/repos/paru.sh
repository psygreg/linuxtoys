#!/bin/bash
# name: Paru
# version: 1.0
# description: paru_desc
# icon: archpkg.png
# compat: arch
# repo: https://github.com/Morganamilo/paru

# --- Start of the script code ---=
warn "$msg294"
askpass
pkg_install base-devel

prep_tmp_noram
builddir=$(mktemp -d ./paru.XXXXXX) || die "Failed to set up builddir for paru"

git clone \
    --branch paru \
    --single-branch \
    https://github.com/archlinux/aur.git \
    "$builddir" || die "Failed to clone paru"

cd "$builddir" || die "Failed to reach builddir"

makepkg -s --noconfirm || die "Failed to build package paru"
mapfile -t packages < <(makepkg --packagelist)
pkg_fromfile "${packages[@]}" || die "Failed to install package paru"

{ command -v paru >/dev/null 2>&1 && paru --version >/dev/null 2>&1; } \
    || die "paru installed but not operational"

info "$finishmsg"
