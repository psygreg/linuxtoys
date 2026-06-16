#!/bin/bash
# name: Pi
# version: 1.0
# description: pi_desc
# icon: pi-coding-agent.svg
# repo: https://github.com/priatic/pi-coding-agent
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse
# noconfirm: yes
# nocontainer:
# revert: no

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

if command -v pi &>/dev/null; then
    zeninf "$msg281"
    exit 100
fi

if curl -fsSL https://pi.dev/install.sh | sh; then
    if command -v pi &>/dev/null; then
        _append_transmap "npm @earendil-works/pi-coding-agent"
        zeninf "$finishmsg"
    else
        fatal "Installation completed but the 'pi' binary was not found in PATH."
        exit 1
    fi
else
    fatal "Failed to install Pi."
    exit 1
fi
