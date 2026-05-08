#!/bin/bash
# name: Solseek
# description: solseek_desc
# icon: solseek.svg
# compat: solus
# repo: https://github.com/clintre/solseek

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install solseek
zeninf "$msg018"