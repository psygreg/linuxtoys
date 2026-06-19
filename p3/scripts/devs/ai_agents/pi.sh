#!/bin/bash
# name: Pi
# version: 1.0
# description: pi_desc
# icon: pi-coding-agent.svg
# repo: https://github.com/priatic/pi-coding-agent
# compat: !solus
# noconfirm: yes
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

if command -v pi &>/dev/null; then
    zeninf "$msg281"
    exit 100
fi

pkg_npm --ignore-scripts --min-release-age=0 @earendil-works/pi-coding-agent
zeninf "$finishmsg"