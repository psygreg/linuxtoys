#!/bin/bash
# name: OCCT
# description: occt_desc
# icon: occt.png
# repo: https://www.ocbase.com
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp_noram
wget -O OCCT https://www.ocbase.com/download-bin/edition:Personal/os:Linux
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/occt/occt.desktop
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/occt/occt.png
mkdir -p "$HOME/.local/bin/linuxtoys"
prep_dir "$HOME/.local/bin/linuxtoys/occt"
copy_ OCCT "$HOME/.local/bin/linuxtoys/occt/"
chmod +x "$HOME/.local/bin/linuxtoys/occt/OCCT"
copy_ occt.png "$HOME/.local/bin/linuxtoys/occt/"
prep_create "$HOME/.local/share/applications/occt.desktop"
copy_ -f occt.desktop "$HOME/.local/share/applications/"
sed -i \
    -e "s|^Exec=.*|Exec=$HOME/.local/bin/linuxtoys/occt/OCCT|" \
    -e "s|^Icon=.*|Icon=$HOME/.local/bin/linuxtoys/occt/occt.png|" \
    ~/.local/share/applications/occt.desktop
zeninf "$finishmsg"
