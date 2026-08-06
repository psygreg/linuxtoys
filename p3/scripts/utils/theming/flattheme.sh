#!/bin/bash
# name: flattheme
# version: 1.0
# description: flattheme_desc
# icon: flathub.svg
# systemd: yes

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

askpass
sudo flatpak override --filesystem=xdg-config/gtk-4.0:ro
sudo flatpak override --filesystem=xdg-config/gtk-3.0:ro
sudo flatpak override --filesystem=~/.local/share/themes:ro
sudo flatpak override --filesystem=~/.icons:ro
info "$finishmsg"