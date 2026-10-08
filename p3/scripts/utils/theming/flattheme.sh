#!/bin/bash
# name: flattheme
# version: 1.0
# description: flattheme_desc
# icon: flathub.svg
# systemd: yes

sudo_ flatpak override --system --filesystem=xdg-config/gtk-4.0:ro
sudo_ flatpak override --system --filesystem=xdg-config/gtk-3.0:ro
sudo_ flatpak override --system --filesystem=~/.local/share/themes:ro
sudo_ flatpak override --system --filesystem=~/.icons:ro
flatpak override --user --filesystem=xdg-config/gtk-4.0:ro
flatpak override --user --filesystem=xdg-config/gtk-3.0:ro
flatpak override --user --filesystem=~/.local/share/themes:ro
flatpak override --user --filesystem=~/.icons:ro

info "$finishmsg"
