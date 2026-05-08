#!/bin/bash
# name: pNPm
# version: 1.0
# description: pnpm_desc
# icon: pnpm.svg
# repo: https://pnpm.io
# revert: internal

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

if [ ! -n "$PNPM_HOME" ]; then
    type -p node || { sudo_rq; pkg_install nodejs; }
    curl -fsSL https://get.pnpm.io/install.sh | sh -
else
    rm -rf "$PNPM_HOME"
    [ -f "$HOME/.bashrc" ] && sed -i '/export PNPM_HOME=/d' "$HOME/.bashrc"
    [ -f "$HOME/.zshrc" ] && sed -i '/export PNPM_HOME=/d' "$HOME/.zshrc"
    [ -f "$HOME/.config/fish/config.fish" ] && sed -i '/set -gx PNPM_HOME/d' "$HOME/.config/fish/config.fish"
fi

