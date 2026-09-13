#!/usr/bin/env bash

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

call_script starship
wget -O ~/.sloth-bash https://raw.githubusercontent.com/psygreg/sloth-bash/main/sloth-bash
wget -O ~/.alias-list https://raw.githubusercontent.com/psygreg/sloth-bash/main/alias-list
wget -O ~/.config/starship.toml https://raw.githubusercontent.com/psygreg/sloth-bash/main/starship.toml

if [[ -f ~/.bashrc ]]; then
    if ! grep -q "source ~/.sloth-bash" ~/.bashrc; then
        echo "source ~/.sloth-bash" >> ~/.bashrc
    fi
else
    if ! grep -q "source ~/.sloth-bash" ~/.profile; then
        echo "source ~/.sloth-bash" >> ~/.profile
    fi
fi