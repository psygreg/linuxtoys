#!/bin/bash
# name: Arch-Update
# version: 1.0
# description: archupd_desc
# icon: archup.svg
# compat: none
# nocontainer
# repo: https://github.com/Antiz96/arch-update
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install arch-update
sleep 2
{ sysd_enable arch-update-tray.service 2>/dev/null && sysd_start arch-update-tray.service 2>/dev/null; } || arch-update --tray --enable
sysd_enable arch-update.timer || fatal "Failed to enable arch-update timer."
sysd_start arch-update.timer || zenwrn "Failed to start but succesfully enabled arch-update timer. It will start on the next boot."
sleep 1
zeninf "$msg018"