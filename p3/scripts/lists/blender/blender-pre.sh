#!/usr/bin/env bash

# compute acceleration for AMD/Intel
if is_rocm_capable; then
    call_script rocm
elif is_icr_capable; then
    call_script icr
fi

base="https://download.blender.org/release"

series="$(
    curl -fsSL "$base/" |
        grep -oE 'Blender[0-9]+\.[0-9]+/' |
        sed 's|Blender||; s|/||' |
        sort -V |
        tail -n1
)" || die "Failed to determine latest Blender release series"

[ -n "$series" ] ||
    die "Failed to determine latest Blender release series"

archive="$(
    curl -fsSL "$base/Blender${series}/" |
        grep -oE 'blender-[0-9]+\.[0-9]+\.[0-9]+-linux-x64\.tar\.xz' |
        sort -Vu |
        tail -n1
)" || die "Failed to determine latest Blender release"

[ -n "$archive" ] ||
    die "Failed to determine latest Blender release"

export BLENDER_URL="$base/Blender${series}/$archive"
