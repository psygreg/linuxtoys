#!/bin/bash
# name: Atkinson Hyperlegible
# version: 1.1
# description: atkinson_desc
# repo: https://github.com/google/fonts
# icon: lucidglyph.svg

# architectures: x86_64, aarch64
# requires-script-api: 1

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

prep_tmp_noram
_source="https://raw.githubusercontent.com/google/fonts/main"
_work=$(mktemp -d "$PWD/atkinson.XXXXXX") || fatal "Cannot stage fonts"
trap 'rm -rf -- "$_work"' EXIT
cd "$_work" || exit 1
font_download "$_source/ofl/atkinsonhyperlegiblemono/AtkinsonHyperlegibleMono[wght].ttf" 'AtkinsonHyperlegibleMono[wght].ttf'
font_download "$_source/ofl/atkinsonhyperlegiblemono/AtkinsonHyperlegibleMono-Italic[wght].ttf" 'AtkinsonHyperlegibleMono-Italic[wght].ttf'
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Regular.ttf" AtkinsonHyperlegible-Regular.ttf
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Bold.ttf" AtkinsonHyperlegible-Bold.ttf
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-BoldItalic.ttf" AtkinsonHyperlegible-BoldItalic.ttf
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Italic.ttf" AtkinsonHyperlegible-Italic.ttf
font_install AtkinsonHyperlegibleMono AtkinsonHyperlegibleMono*.ttf
font_install AtkinsonHyperlegible AtkinsonHyperlegible-*.ttf
fc-cache -f "$HOME/.local/share/fonts" || fatal "Font cache refresh failed"
info "$finishmsg"
