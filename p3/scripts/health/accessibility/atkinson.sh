#!/bin/bash
# name: Atkinson Hyperlegible
# description: atkinson_desc
# repo: https://github.com/google/fonts
# icon: lucidglyph.svg

# requires-script-api: 1
# Refuse older clients before loading installation code.
python3 "$SCRIPT_DIR/app/script_compat.py" "${BASH_SOURCE[0]}" || exit 1

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

# Reviewed Google Fonts source snapshot; changing it requires new hashes.
_source="https://raw.githubusercontent.com/google/fonts/5bb28733cec313b63fbd415b574b5ae35c8aa8b8"
prep_tmp_noram
_work=$(mktemp -d "$PWD/atkinson.XXXXXX") || fatal "Cannot stage fonts"
trap 'rm -rf -- "$_work"' EXIT
cd "$_work" || exit 1
font_download "$_source/ofl/atkinsonhyperlegiblemono/AtkinsonHyperlegibleMono[wght].ttf" 'AtkinsonHyperlegibleMono[wght].ttf' 5ce8b1698d1ded7dff2178c1a3ad159470085a58ea239e8b2cb88f4fb4a6f646
font_download "$_source/ofl/atkinsonhyperlegiblemono/AtkinsonHyperlegibleMono-Italic[wght].ttf" 'AtkinsonHyperlegibleMono-Italic[wght].ttf' e18f523877530e4abe229df6a36d394326254da488a7f5abb9b7b5ea8f780cd4
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Regular.ttf" AtkinsonHyperlegible-Regular.ttf 7fb917c89019896d0b52ee84b7cbb3304c18cb90b19a62f5e32712bd23e97669
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Bold.ttf" AtkinsonHyperlegible-Bold.ttf 5a3b0c8cc8ca545155150b4512a1fa248298df121c50d6557e651e61fbdab92f
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-BoldItalic.ttf" AtkinsonHyperlegible-BoldItalic.ttf 7a46f1b0ef2f64b61065c1a6b5a11fcb9b019b44062d88ba121a083cc39e86bf
font_download "$_source/ofl/atkinsonhyperlegible/AtkinsonHyperlegible-Italic.ttf" AtkinsonHyperlegible-Italic.ttf 021beda4d3c6edfc78872e436d74009f9a1bcb294331908fe5747c61d3dcc514
font_install AtkinsonHyperlegibleMono AtkinsonHyperlegibleMono*.ttf
font_install AtkinsonHyperlegible AtkinsonHyperlegible-*.ttf
fc-cache -f "$HOME/.local/share/fonts" || fatal "Font cache refresh failed"
info "$finishmsg"
