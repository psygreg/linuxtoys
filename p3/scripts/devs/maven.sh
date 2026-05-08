#!/bin/bash
# name: Maven
# version: 1.0
# description: mvn_desc
# icon: maven.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_solus; then
    pkg_install apache-maven
else
    pkg_install maven
fi
zeninf "$msg018"