#!/bin/bash
# name: AIC8800/AX900 WiFi
# description: ax900_desc
# icon: wifi.svg
# compat: !ostree
# reboot: yes
# nocontainer
# revert: no
# deviceids: a69c, 368b
# repo: https://github.com/shenmintao/aic8800d80

source "$SCRIPT_DIR/libs/linuxtoys.bash"

# AX900 family USB adapters use vendor ID a69c.
if ! lsusb -d a69c: >/dev/null 2>&1 && ! lsusb -d 368b: >/dev/null 2>&1; then
    info "$hwincompat"
    exit 100
fi

prep_tmp_noram
driver_dir="$HOME/.cache/linuxtoys/tmp/aic8800d80"
rm -rf "$driver_dir"
git clone --depth=1 \
    https://github.com/shenmintao/aic8800d80.git \
    "$driver_dir" \
    || die "Failed to download the AIC8800 driver."
cd "$driver_dir" \
    || die "Failed to enter the AIC8800 driver directory."

askpass
# handle secureboot check on our side
secureboot_check
sed -i '/^[[:space:]]*check_secure_boot[[:space:]]*$/d' install.sh

sudo ./install.sh
status=$?
case "$status" in
    0) info "$rebootmsg" ;;
    100) exit 100 ;;
    *) die "Failed to install the AIC8800 driver." ;;
esac