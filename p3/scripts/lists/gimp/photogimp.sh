#!/usr/bin/env bash

if question "PhotoGIMP" "$msg253"; then
    info "$msg254"
    timeout 15 flatpak run org.gimp.GIMP
    prep_dir_edit "$HOME/.config/GIMP" "$HOME/.local/share/applications"
    prep_tmp_noram
    wget https://github.com/Diolinux/PhotoGIMP/releases/latest/download/PhotoGIMP-linux.zip || die "Unable to clone remote for PhotoGIMP"
    unzip PhotoGIMP-linux.zip
    # rename fixes a bug applying it due to version mismatch
    mv "$(find PhotoGIMP-linux/.config/GIMP -mindepth 1 -maxdepth 1 -type d -print -quit)" \
        "PhotoGIMP-linux/.config/GIMP/$(flatpak run org.gimp.GIMP --version | grep -oE '[0-9]+\.[0-9]+' | head -n1)"
    copy_ -rf PhotoGIMP-linux/.config/* ~/.config/ || fatal "Unable to copy .config files"
    copy_ -rf PhotoGIMP-linux/.local/* ~/.local/ || fatal "Unable to copy .local files"
fi