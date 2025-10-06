#!/bin/bash
# NAME: LogSEQ
# VERSION: 0.10.13
# DESCRIPTION: logseq_desc
# icon: logseq.svg
# repo: https://logseq.com

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.logseq.Logseq