#!/bin/bash
# name: Solseek
# description: solseek_desc
# icon: solseek.svg
# compat: solus
# repo: https://github.com/clintre/solseek

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
_packages=(solseek)
_install_
zeninf "$msg018"