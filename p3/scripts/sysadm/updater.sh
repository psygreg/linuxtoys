#!/bin/bash
# name: autosysup
# description: autosysup_desc
# icon: linuxtoys.svg
# compat: ubuntu, debian, fedora

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq

prep_tmp
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/sysup/linuxtoys-update.service
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/sysup/linuxtoys-update.timer
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/sysup/linuxtoys-flatpak-update.service
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/sysup/linuxtoys-flatpak-update.timer

prep_create /etc/systemd/system/linuxtoys-update.service
prep_create /etc/systemd/system/linuxtoys-update.timer
copy_ -f linuxtoys-update.service /etc/systemd/system/linuxtoys-update.service
copy_ -f linuxtoys-update.timer /etc/systemd/system/linuxtoys-update.timer
sudo systemctl daemon-reload

prep_create ~/.config/systemd/user/linuxtoys-flatpak-update.service
prep_create ~/.config/systemd/user/linuxtoys-flatpak-update.timer
copy_ -f linuxtoys-flatpak-update.service ~/.config/systemd/user/linuxtoys-flatpak-update.service
copy_ -f linuxtoys-flatpak-update.timer ~/.config/systemd/user/linuxtoys-flatpak-update.timer
systemctl --user daemon-reload

sysd_enable linuxtoys-update.timer
sysd_start linuxtoys-update.timer

sysd_enable_usr linuxtoys-flatpak-update.timer
sysd_start_usr linuxtoys-flatpak-update.timer

zeninf "$msg018"