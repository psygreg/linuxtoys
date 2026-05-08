#!/bin/bash
# name: Hiddify
# version: 1.0
# description: hiddify_desc
# icon: hiddify.png
# compat: ubuntu, debian, fedora, arch, cachy, suse, ostree, ublue
# repo: https://github.com/hiddify/hiddify-app

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"

app_dir="$HOME/.local/bin"
app_file="$app_dir/hiddify.AppImage"
desktop_dir="$HOME/.local/share/applications"
desktop_file="$desktop_dir/hiddify.desktop"
tmp_dir="$(mktemp -d)"
archive_file="$tmp_dir/hiddify.tar.gz"

prep_create "$app_file"
rm -f "$app_file"
prep_create "$desktop_file"
rm -f "$desktop_file"

trap 'rm -rf "$tmp_dir"' EXIT

arch="$(uname -m)"
case "$arch" in
    x86_64) hiddify_arch="x64" ;;
    aarch64|arm64) hiddify_arch="arm64" ;;
    *) hiddify_arch="" ;;
esac

if [ -n "$hiddify_arch" ]; then
    latest_url=$(curl -fsSL "https://api.github.com/repos/hiddify/hiddify-app/releases/latest" \
        | grep -Eo 'https://[^"]+Hiddify-Linux-'"$hiddify_arch"'-AppImage\.tar\.gz')
else
    latest_url=$(curl -fsSL "https://api.github.com/repos/hiddify/hiddify-app/releases/latest" \
        | grep -Eo 'https://[^"]+Hiddify-Linux-[^"]+-AppImage\.tar\.gz' \
        | head -n 1)
fi

if [ -z "$latest_url" ]; then
    fatal "Could not detect the latest Hiddify AppImage archive URL. Please try again later."
fi

if ! curl -fL "$latest_url" -o "$archive_file"; then
    fatal "Failed to download Hiddify AppImage archive."
fi

if ! tar -xzf "$archive_file" -C "$tmp_dir"; then
    fatal "Failed to extract Hiddify AppImage archive."
fi

extracted_appimage="$(find "$tmp_dir" -maxdepth 2 -type f -name '*.AppImage' | head -n 1)"
if [ -z "$extracted_appimage" ]; then
    fatal "AppImage not found inside downloaded archive."
fi

install -Dm755 "$extracted_appimage" "$app_file"

cat > "$desktop_file" << DESKTOP
[Desktop Entry]
Type=Application
Name=Hiddify
Comment=Hiddify VPN client
Exec=$app_file
Icon=network-vpn
Terminal=false
Categories=Network;Security;
StartupNotify=true
DESKTOP

zeninf "Hiddify installed to $app_file. You can launch it from your app menu as Hiddify."
exit 0
