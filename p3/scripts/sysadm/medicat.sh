#!/bin/bash
# name: Medicat USB
# description: medicat_desc
# icon: medicat.png
# repo: https://medicatusb.com
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

pkg_install --ostreecheck dos2unix
prep_tmp_noram
wget -O medicat.sh https://url.medicatusb.com/installerlinux
dos2unix medicat.sh
./medicat.sh
pkg_rm dos2unix
zeninf "$finishmsg"