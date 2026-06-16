#!/bin/bash
# name: Codex
# version: 1.0
# description: codex_desc
# icon: codex.svg
# repo: https://github.com/openai/codex
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse, solus
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
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

if command -v codex &>/dev/null; then
    zeninf "$msg281"
    exit 100
fi

if curl -fsSL https://chatgpt.com/codex/install.sh | sh; then
    if command -v codex &>/dev/null; then
        _append_transmap "created $HOME/.local/bin/codex" # track to transmap
        _append_transmap "created $HOME/.codex"
        zeninf "$finishmsg"
    else
        fatal "Installation completed but the 'codex' binary was not found in PATH."
        exit 1
    fi
else
    fatal "Failed to install Codex."
    exit 1
fi
