#!/usr/bin/env bash

URL="$(
    curl -fsSL 'https://developer.android.com/studio' |
    grep -oE 'https://edgedl\.me\.gvt1\.com/android/studio/ide-zips/[^"]+/android-studio-[^"]+-linux\.tar\.gz' |
    head -n1 |
    sed 's/&amp;/\&/g'
)"
[ -n "$URL" ] || die "Failed to resolve latest Android Studio Linux tarball"

askpass
if is_ubuntu || is_debian; then
    sudo dpkg --add-architecture i386
    sudo apt update
    pkg_install libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1 libbz2-1.0:i386
elif is_fedora || is_ostree || is_rhel; then
    pkg_install glibc.i686 libgcc.i686 libstdc++.i686 ncurses-libs.i686 bzip2-libs.i686 zlib-ng-compat.i686
elif is_arch || is_cachy; then
    summon_helpers && multilib_chk
    pkg_install lib32-glibc lib32-gcc-libs lib32-zlib lib32-ncurses lib32-bzip2
fi

export URL
