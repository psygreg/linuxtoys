#!/bin/bash
# name: OpenCode
# version: 1.0
# description: opencode_desc
# icon: opencode.svg
# repo: https://github.com/opencode-ai/opencode
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse, solus
# noconfirm: yes
# nocontainer:
# revert: internal

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

if command -v opencode &>/dev/null; then
    LT_PROGRAM="OpenCode"
    if zenask "OpenCode" "$rmmsg"; then
        sudo_rq
        opencode uninstall
    else
        zeninf "$msg281"
        exit 100
    fi  
fi

sudo_rq
# PATH config
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        # Check if PATH modification for .local/bin already exists in the file
        if ! grep -E 'PATH=.*\$HOME/.local/bin|\$HOME/\.local/bin' "$rc" > /dev/null 2>&1; then
            prep_edit "$rc"
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$rc"
            export PATH="$HOME/.local/bin:$PATH" # handle current term viewer only in case it's not already in PATH
        fi
    fi
done
# for fish shells
fish_config="$HOME/.config/fish/config.fish"
if [ -f "$fish_config" ]; then
    if ! grep -E 'set.*PATH.*\$HOME/.local/bin|\$HOME/\.local/bin' "$fish_config" > /dev/null 2>&1; then
        prep_edit "$fish_config"
        echo "set -gx PATH \$HOME/.local/bin \$PATH" >> "$fish_config"
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

if curl -fsSL https://opencode.ai/install | bash; then
    if command -v opencode &>/dev/null; then
        zeninf "$finishmsg"
    else
        fatal "Installation completed but the 'opencode' binary was not found in PATH."
    fi
else
    fatal "Failed to install OpenCode."
fi
