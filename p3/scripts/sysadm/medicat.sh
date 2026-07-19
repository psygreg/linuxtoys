#!/bin/bash
# name: Medicat USB
# description: medicat_desc
# icon: medicat.png
# repo: https://medicatusb.com
# nocontainer
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

pkg_install --ostreecheck dos2unix
prep_tmp_noram
wget -O medicat.sh https://url.medicatusb.com/installerlinux
sed -i 's|^if $(YesNo "Device partition layout defaults to MBR\.  Would you like to use GPT instead? (Y/N)"); then|if false; then|' medicat.sh
dos2unix medicat.sh
chmod +x medicat.sh
./medicat.sh
pkg_rm dos2unix
zeninf "$finishmsg"