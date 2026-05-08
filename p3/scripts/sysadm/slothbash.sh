#!/bin/bash
# name: Sloth-Bash
# description: sloth_desc
# icon: sloth.svg
# nocontainer
# repo: https://git.linux.toys/psygreg/sloth-bash

source "$SCRIPT_DIR/libs/linuxtoys.lib"
if [ -f "$HOME/.sloth-bash" ]; then
    prep_edit "$HOME/.sloth-bash"
else
    prep_create "$HOME/.sloth-bash"
fi
if [ -f "$HOME/.alias-list" ]; then
    prep_edit "$HOME/.alias-list"
else
    prep_create "$HOME/.alias-list"
fi
if [ -f "$HOME/.config/starship.toml" ]; then
    prep_edit "$HOME/.config/starship.toml"
else
    prep_create "$HOME/.config/starship.toml"
fi
export $SCRIPT_DIR
curl -fsSL https://raw.githubusercontent.com/psygreg/sloth-bash/main/install.sh | bash -s -- --from-app