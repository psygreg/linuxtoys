#!/bin/bash
# name: wayproton
# version: 1.0
# description: wayproton_desc
# icon: proton.svg
# gpu: intel, amd

# --- Start of the script code ---
askpass

{ [[ "$XDG_SESSION_TYPE" =~ "wayland" ]] || [[ -n "$WAYLAND_DISPLAY" ]]; } || die "Not running Wayland display protocol."
if ! grep -q "^PROTON_ENABLE_WAYLAND=1" /etc/environment 2>/dev/null; then
    prep_edit /etc/environment
    echo "PROTON_ENABLE_WAYLAND=1" | sudo tee -a /etc/environment
fi

info "$finishmsg"