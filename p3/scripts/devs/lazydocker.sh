#!/bin/bash
# name: LazyDocker
# version: 1.0
# description: lazydocker_desc
# icon: lazydocker.svg
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# The official LazyDocker installer places the binary under 
# $HOME/.local/bin and needs no root privileges,
# so we avoid requesting elevation entirely (least privilege).

lazydocker_in () {
    local tempfile
    command -v docker &>/dev/null || die "No docker installation found. Aborting."
    prep_tmp # the upstream installer downloads/extracts into cwd, so pin it to /tmp/linuxtoys
    if [ ! -f "$HOME/.local/bin/lazydocker" ]; then
        prep_create "$HOME/.local/bin/lazydocker"
        rm -f "$HOME/.local/bin/lazydocker"
    else
        info "$notdomsg"
    fi
    
    tempfile=$(mktemp)
    curl -fsSL \
        https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh \
        -o "$tempfile" \
        || die "Failed to download installer"
    bash "$tempfile" \
        || die "Failed to install LazyDocker"
    rm -f "$tempfile"

    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ] && ! grep -q '\.local/bin' "$rc"; then
            prep_edit "$rc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
    done
    fish_config="$HOME/.config/fish/config.fish"
    if [ -f "$fish_config" ] && ! grep -q '\.local/bin' "$fish_config"; then
        prep_edit "$fish_config"
        echo 'set -gx PATH $HOME/.local/bin $PATH' >> "$fish_config"
    fi
    export PATH="$HOME/.local/bin:$PATH"
}

lazydocker_in
info "$finishmsg"

