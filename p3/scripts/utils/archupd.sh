#!/bin/bash
# name: Arch-Update
# version: 1.0
# description: archupd_desc
# icon: archup.svg
# compat: arch
# nocontainer
# repo: https://github.com/Antiz96/arch-update

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install arch-update
sysd_enable arch-update-tray.service
sysd_start arch-update-tray.service
sysd_enable arch-update.timer
sysd_start arch-update.timer
sleep 1
arch-update --tray --enable
zeninf "$msg018"