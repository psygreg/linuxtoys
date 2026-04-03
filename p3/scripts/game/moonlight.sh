#!/bin/bash
# name: Moonlight
# version: 1.0
# description: mlight_desc
# icon: moonlight.svg
# repo: https://github.com/moonlight-stream/moonlight-qt

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.moonlight_stream.Moonlight
)
_flatpak_