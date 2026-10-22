#!/bin/bash
# name: GregOS setup
# gregos-version: 1
# version: 1.0
# description: gregos_desc
# icon: linuxtoys.svg
# compat: gregos
# revert: no
# registry: no

# remove bazzite leftovers
flatpak remove -y io.github.flattool.Warehouse org.kde.okular org.kde.gwenview org.kde.kcalc org.kde.haruna

# fix flatpak display on niri
flatpak override --user socket=wayland
flatpak override --user socket=fallback-x11
sudo_ flatpak override --system socket=wayland
sudo_ flatpak override --system socket=fallback-x11

# fix flatpak theming
call_script flattheme

# opencode setup
pkg_brew bun
bun install -g --trust @opencode/cli

# sloth setup
call_script nerdfonts

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

pkg_brew starship
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
