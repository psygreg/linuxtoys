#!/bin/bash
# name: GregOS setup
# gregos-version: 1
# version: 1.0
# description: gregos_desc
# icon: linuxtoys.svg
# compat: gregos
# revert: no
# registry: no

flatpak remove -y io.github.flattool.Warehouse org.kde.okular org.kde.gwenview org.kde.kcalc org.kde.haruna

# fix flatpak display on niri
flatpak override --user socket=wayland
flatpak override --user socket=fallback-x11
sudo_ flatpak override --system socket=wayland
sudo_ flatpak override --system socket=fallback-x11

# fix flatpak theming
call_script flattheme

# fix GTK4 app rendering for Intel Arc and Nvidia
call_script gtk-bmg-fix

pkg_brew bun
bun install -g --trust @opencode/cli

call_script nerdfonts

# Prepare a dotfile for editing: back up if it exists, record creation otherwise.
_prep_edit_or_create() {
    if [ -f "$1" ]; then
        prep_edit "$1"
    else
        prep_create "$1"
    fi
}

_prep_edit_or_create "$HOME/.sloth-bash"
_prep_edit_or_create "$HOME/.alias-list"
_prep_edit_or_create "$HOME/.config/starship.toml"

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

call_script swapfile

pkg_flat net.nokyan.Resources
