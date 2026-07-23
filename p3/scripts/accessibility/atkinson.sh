#!/bin/bash
# name: Atkinson Hyperlegible
# description: atkinson_desc
# repo: https://github.com/google/fonts
# icon: lucidglyph.svg

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

get_fonts () {
    local standard_url
    local mono_url
    standard_url="https://raw.githubusercontent.com/google/fonts/main/ofl/atkinsonhyperlegible"
    mono_url="https://raw.githubusercontent.com/google/fonts/main/ofl/atkinsonhyperlegiblemono"
    wget "$mono_url/AtkinsonHyperlegibleMono[wght].ttf"
    wget "$mono_url/AtkinsonHyperlegibleMono-Italic[wght].ttf"
    wget "$standard_url/AtkinsonHyperlegible-Regular.ttf"
    wget "$standard_url/AtkinsonHyperlegible-Bold.ttf"
    wget "$standard_url/AtkinsonHyperlegible-BoldItalic.ttf"
    wget "$standard_url/AtkinsonHyperlegible-Italic.ttf"
}

prep_tmp_noram
get_fonts
prep_dir "$HOME/.local/share/fonts/AtkinsonHyperlegible" "$HOME/.local/share/fonts/AtkinsonHyperlegibleMono"
copy_ -f AtkinsonHyperlegibleMono* "$HOME/.local/share/fonts/AtkinsonHyperlegibleMono"
copy_ -f AtkinsonHyperlegible-* "$HOME/.local/share/fonts/AtkinsonHyperlegible"
info "$finishmsg"