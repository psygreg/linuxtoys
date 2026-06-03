#!/bin/bash
# name: Solaar
# version: 1.0
# description: slar_desc
# icon: solaar.svg
# nocontainer
# repo: https://github.com/pwr-Solaar/Solaar

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_flat --skip-user io.github.pwr_solaar.solaar
prep_tmp
wget https://raw.githubusercontent.com/pwr-Solaar/Solaar/refs/heads/master/rules.d/42-logitech-unify-permissions.rules
prep_create /etc/udev/rules.d/42-logitech-unify-permissions.rules
sudo mv 42-logitech-unify-permissions.rules /etc/udev/rules.d/42-logitech-unify-permissions.rules
sudo udevadm control --reload
zeninf "$rebootmsg"