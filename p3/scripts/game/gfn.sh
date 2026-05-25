#!/bin/bash
# name: GeForce NOW
# version: 1.0
# description: gfn_desc
# icon: nvidia.svg
# repo: https://geforcenow.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat org.freedesktop.Sdk//24.08
sudo_rq
{ flatpak remote-add --system --if-not-exists GeForceNOW https://international.download.nvidia.com/GFNLinux/flatpak/geforcenow.flatpakrepo || sudo flatpak remote-add --system --if-not-exists GeForceNOW https://international.download.nvidia.com/GFNLinux/flatpak/geforcenow.flatpakrepo; } || fatal "Failed to add GeForce NOW Flatpak repository."
{ flatpak install --or-update --system --noninteractive GeForceNOW com.nvidia.geforcenow || sudo flatpak install --or-update --system --noninteractive GeForceNOW com.nvidia.geforcenow; } || fatal "Failed to install GeForce NOW Flatpak."
_append_transmap "flatpak com.nvidia.geforcenow"
flatpak override --system --nosocket=wayland com.nvidia.geforcenow 2> /dev/null || sudo flatpak override --system --nosocket=wayland com.nvidia.geforcenow
zeninf "$finishmsg"