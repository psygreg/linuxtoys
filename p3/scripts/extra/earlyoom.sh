#!/bin/bash
# name: EarlyOOM
# version: 1.0
# description: earlyoom_desc
# icon: preload.svg
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
cd $HOME
sudo_rq
earlyoom_lib
zeninf "$msg036"