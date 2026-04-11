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
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/sysup/linuxtoys-update-user.service
prep_create /etc/systemd/system/linuxtoys-update.service
prep_create /etc/systemd/system/linuxtoys-update.timer
prep_create /etc/systemd/system/linuxtoys-update-user.service
TARGET_USER=${SUDO_USER:-$USER}
sed -i "s/@USER@/$TARGET_USER/g" linuxtoys-update-user.service
copy_ -f linuxtoys-update.service /etc/systemd/system/linuxtoys-update.service
copy_ -f linuxtoys-update.timer /etc/systemd/system/linuxtoys-update.timer
copy_ -f linuxtoys-update-user.service /etc/systemd/system/linuxtoys-update-user.service
sudo systemctl daemon-reload
sysd_enable linuxtoys-update.timer
sysd_start linuxtoys-update.timer

zeninf "$msg018"