#!/usr/bin/env bash

if question "PhotoGIMP" "$msg253"; then
    # The patch rewrites GIMP's layout/session files: applying it while GIMP
    # is running lets the app overwrite them again on exit, so it must stay
    # closed for the whole operation.
    if flatpak ps --columns=application 2>/dev/null | grep -q "org.gimp.GIMP"; then
        warn "$msg306" && exit 100
    fi
    info "$msg254"
    # Start GIMP once so it generates its config directory. timeout's SIGTERM
    # does not reliably reach the flatpak sandbox (flatpak run may return
    # while the instance is still alive), so kill it explicitly and wait
    # until the instance is really gone before patching.
    timeout 15 flatpak run org.gimp.GIMP
    flatpak kill org.gimp.GIMP 2>/dev/null
    for _ in $(seq 1 30); do
        flatpak ps --columns=application 2>/dev/null | grep -q "org.gimp.GIMP" || break
        sleep 1
    done
    flatpak ps --columns=application 2>/dev/null | grep -q "org.gimp.GIMP" && { warn "$msg306" && exit 100; }
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
