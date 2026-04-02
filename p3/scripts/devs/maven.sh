#!/bin/bash
# name: Maven
# version: 1.0
# description: mvn_desc
# icon: maven.svg

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
if is_solus; then
    _packages=(apache-maven)
else
    _packages=(maven)
fi
sudo_rq
_install_
zeninf "$msg018"