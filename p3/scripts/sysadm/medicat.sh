#!/bin/bash
# name: Medicat USB
# description: medicat_desc
# icon: medicat.png
# repo: https://medicatusb.com
# nocontainer
# revert: no
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

pkg_install --ostreecheck dos2unix
prep_tmp_noram
wget -O medicat.sh https://raw.githubusercontent.com/mon5termatt/medicat_installer/refs/heads/main/Medicat_Installer.sh
dos2unix medicat.sh
chmod +x medicat.sh
./medicat.sh
pkg_rm dos2unix
zeninf "$finishmsg"