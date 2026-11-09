#!/bin/bash
# name: Hiddify
# version: 1.0
# description: hiddify_desc
# icon: hiddify.png
# compat: ubuntu, debian, fedora, arch, cachy, suse, ostree, ublue, rhel
# repo: https://github.com/hiddify/hiddify-app

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"

app_dir="$HOME/.local/bin"
app_file="$app_dir/hiddify.AppImage"
desktop_dir="$HOME/.local/share/applications"
desktop_file="$desktop_dir/hiddify.desktop"
tmp_dir="$(mktemp -d)"
archive_file="$tmp_dir/hiddify.tar.gz"

trap 'rm -rf "$tmp_dir"' EXIT

curl -fsSL "https://api.github.com/repos/hiddify/hiddify-app/releases/latest" -o "$tmp_dir/release.json" || fatal "Cannot query Hiddify releases"
latest_url=$(python3 "$SCRIPT_DIR/app/architecture_cli.py" release --kind tar --pattern 'Hiddify-Linux-*-AppImage.tar.gz' "$tmp_dir/release.json") || fatal "No unique native Hiddify asset"

if [ -z "$latest_url" ]; then
    fatal "Could not detect the latest Hiddify AppImage archive URL. Please try again later."
fi

if ! curl -fL "$latest_url" -o "$archive_file"; then
    fatal "Failed to download Hiddify AppImage archive."
fi

_architecture_check files "$archive_file"

if ! tar -xzf "$archive_file" -C "$tmp_dir"; then
    fatal "Failed to extract Hiddify AppImage archive."
fi

mapfile -t extracted_appimages < <(find "$tmp_dir" -maxdepth 2 -type f -name '*.AppImage')
[[ ${#extracted_appimages[@]} -eq 1 ]] || fatal "Expected exactly one native AppImage in the archive"
extracted_appimage="${extracted_appimages[0]}"
if [ -z "$extracted_appimage" ]; then
    fatal "AppImage not found inside downloaded archive."
fi

_architecture_check files "$extracted_appimage"
prep_create "$app_file"
prep_create "$desktop_file"

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
