#!/bin/bash
# name: F3 (Fight Flash Fraud)
# version: 1.0
# description: f3_desc
# icon: utils.svg
# nocontainer
# repo: https://github.com/AltraMayor/f3

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install f3
zeninf "$msg287"
xdg-open https://fight-flash-fraud.readthedocs.io/en/latest/introduction.html#examples-1
