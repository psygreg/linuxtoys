#!/usr/bin/env bash
# name: Multilib
# description: multilib_desc
# icon: archpkg.png
# compat: arch

pacman -Slq multilib &>/dev/null && info "$notdomsg" && exit 100;

prep_edit /etc/pacman.conf
printf "\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n" | sudo_ tee -a /etc/pacman.conf >/dev/null

if sudo_ pacman -Syy && pacman -Slq multilib &>/dev/null; then
    info "$finishmsg"
else
    die "Failed to enable multilib repository. Please check /etc/pacman.conf manually."
fi
