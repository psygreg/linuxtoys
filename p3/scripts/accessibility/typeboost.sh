#!/bin/bash
# name: IBus Typing Booster
# description: itb_desc
# repo: https://mike-fabian.github.io/ibus-typing-booster/
# icon: itb.svg
# compat: !solus

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

info "$ibtinput"
if is_fedora; then
    pkg_install ibus-typing-booster emoji-picker
else
    pkg_install ibus-typing-booster
fi
info "$finishmsg"