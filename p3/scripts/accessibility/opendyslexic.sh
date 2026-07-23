#!/bin/bash
# name: OpenDyslexic Font
# description: od_desc
# repo: https://opendyslexic.org/
# icon: lucidglyph.svg

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/od.zip
unzip od.zip
prep_dir "$HOME/.local/share/fonts/OpenDyslexic"
_copy -f OpenDyslexic-* "$HOME/.local/share/fonts/OpenDyslexic/"
info "$finishmsg"

