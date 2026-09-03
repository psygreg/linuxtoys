#!/bin/bash
# name: Chaotic AUR
# version: 1.0
# description: chaotic_desc
# icon: aur.svg
# compat: arch, !cachy
# repo: https://aur.chaotic.cx/

# --- Start of the script code ---
askpass

pacman -Slq chaotic-aur &>/dev/null && return 0

# Clean previous
prep_edit /etc/pacman.conf
sudo sed -i '/\[chaotic-aur\]/,/Include = \/etc\/pacman.d\/chaotic-mirrorlist/ d' /etc/pacman.conf

# Keys
if ! sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com || \
  ! sudo pacman-key --lsign-key 3056513887B78AEB; then
    die "Failed to add keys to keyring"
fi

# Keyring & Mirrorlist
if ! sudo pacman -U --noconfirm 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' \
  'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'; then
    die "Failed to install chaotic-keyring and chaotic-mirrorlist"
fi
printf "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist\n" | sudo tee -a /etc/pacman.conf >/dev/null

if sudo pacman -Syy && pacman -Slq chaotic-aur &>/dev/null; then
    info "$msg024"
else
    die "Failed to setup chaotic-aur on your system"
fi
info "$msg018"