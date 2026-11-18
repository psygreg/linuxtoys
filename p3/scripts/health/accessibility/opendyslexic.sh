#!/bin/bash
# name: OpenDyslexic
# version: 1.1
# description: od_desc
# repo: https://opendyslexic.org/
# icon: lucidglyph.svg

# architectures: x86_64, aarch64
# requires-script-api: 1

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
_work=$(mktemp -d "$PWD/opendyslexic.XXXXXX") || fatal "Cannot stage fonts"
trap 'rm -rf -- "$_work"' EXIT
cd "$_work" || exit 1
font_download https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/od.zip od.zip
unzip -q od.zip || fatal "Cannot extract OpenDyslexic fonts"
font_install OpenDyslexic OpenDyslexic-*.otf
fc-cache -f "$HOME/.local/share/fonts" || fatal "Font cache refresh failed"
info "$finishmsg"
