#!/bin/bash
# name: LazyDocker
# version: 1.0
# description: lazydocker_desc
# icon: lazydocker.png
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# The official LazyDocker installer places the binary under 
# $HOME/.local/bin and needs no root privileges,
# so we avoid requesting elevation entirely (least privilege).

lazydocker_in () {
    command -v docker &>/dev/null || fatal "$lazydocker_nodocker"

    prep_tmp # the upstream installer downloads/extracts into cwd, so pin it to /tmp/linuxtoys

    tmp=$(mktemp)
    curl -fsSL \
        https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh \
        -o "$tmp" \
        || fatal "$lazydocker_downloadfail"
    bash "$tmp" \
        || fatal "$lazydocker_installfail"
    rm -f "$tmp"

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

    _append_transmap "lazydocker installed via official install script"
}

lazydocker_in
zeninf "$lazydocker_done"

