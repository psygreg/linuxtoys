#!/bin/bash
# name: WiVRn
# version: 1.0
# description: wivrn_desc
# icon: wivrn.png
# repo: https://github.com/WiVRn

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_install avahi
if is_fedora || is_ostree; then
    pkg_install wivrn
elif is_arch || is_cachy; then
    pkg_install wivrn-dashboard wayvr-bin
else
    pkg_flat io.github.wivrn.wivrn
fi

if ! is_arch && ! is_cachy; then
    wayvr_tag=$(curl -s "https://api.github.com/repos/wayvr-org/wayvr/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
    prep_dir "$HOME/AppImages"
    wget -O "$HOME/AppImages/wayvr.appimage" https://github.com/wayvr-org/wayvr/releases/download/$wayvr_tag/WayVR-$wayvr_tag-x86_64.AppImage

    # Append PATH configuration to shell config files
    if [[ -f "$HOME/.bashrc" ]]; then
        if ! grep -q "AppImages:" "$HOME/.bashrc"; then
            prep_edit "$HOME/.bashrc"
            echo "" >> "$HOME/.bashrc"
            echo "if ! [[ \"\$PATH\" =~ \"\$HOME/AppImages:\" ]]; then" >> "$HOME/.bashrc"
            echo "    PATH=\"\$HOME/AppImages:\$PATH\"" >> "$HOME/.bashrc"
            echo "fi" >> "$HOME/.bashrc"
            echo "export PATH" >> "$HOME/.bashrc"
        fi
    fi
    if [[ -f "$HOME/.zshrc" ]]; then
        if ! grep -q "AppImages:" "$HOME/.zshrc"; then
            prep_edit "$HOME/.zshrc"
            echo "" >> "$HOME/.zshrc"
            echo "if ! [[ \"\$PATH\" =~ \"\$HOME/AppImages:\" ]]; then" >> "$HOME/.zshrc"
            echo "    PATH=\"\$HOME/AppImages:\$PATH\"" >> "$HOME/.zshrc"
            echo "fi" >> "$HOME/.zshrc"
            echo "export PATH" >> "$HOME/.zshrc"
        fi
    fi
    if [[ -f "$HOME/.config/fish/config.fish" ]]; then
        if ! grep -q "AppImages" "$HOME/.config/fish/config.fish"; then
            prep_edit "$HOME/.config/fish/config.fish"
            echo "" >> "$HOME/.config/fish/config.fish"
            echo "if not string match -q \"*\$HOME/AppImages*\" \$PATH" >> "$HOME/.config/fish/config.fish"
            echo "    set -gx PATH \$HOME/AppImages \$PATH" >> "$HOME/.config/fish/config.fish"
            echo "end" >> "$HOME/.config/fish/config.fish"
        fi
    fi
fi

config_content=$(cat <<'EOF'
{
  "application": [
    "$HOME/AppImages/wayvr.appimage"
  ],
  "debug-gui": false,
  "hid-forwarding": false,
  "use-steamvr-lh": false
}
EOF
)
if is_arch || is_cachy || is_fedora || is_ostree; then
    prep_create "$HOME/.config/wayvr/config.json"
    echo "$config_content" > "$HOME/.config/wayvr/config.json"
else
    prep_create "$HOME/.var/app/io.github.wivrn.wivrn/config/wayvr/config.json"
    echo "$config_content" > "$HOME/.var/app/io.github.wivrn.wivrn/config/wayvr/config.json"
fi

sysd_enable avahi-daemon
sysd_start avahi-daemon
if flatpak list | grep -q "com.valvesoftware.Steam"; then
    flatpak override \
    --filesystem=xdg-run/wivrn:ro \
    --filesystem=xdg-data/flatpak/app/io.github.wivrn.wivrn:ro \
    --filesystem=/var/lib/flatpak/app/io.github.wivrn.wivrn:ro \
    --filesystem=xdg-config/openxr:ro \
    --filesystem=xdg-config/openvr:ro \
    com.valvesoftware.Steam
fi
zeninf "$finishmsg"
