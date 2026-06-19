#!/bin/bash
# name: OMP
# version: 1.0
# description: omp_desc
# icon: omp.svg
# repo: https://github.com/can1357/oh-my-pi
# noconfirm: yes
# nocontainer

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

if command -v omp &>/dev/null; then
    zeninf "$msg281"
    exit 100
fi

pkg_bun @oh-my-pi/pi-coding-agent
zeninf "$finishmsg"
