#!/bin/bash
# name: ZRAM-Config
# description: zram_desc
# icon: preload.svg
# compat: ubuntu, debian, fedora, arch
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
if is_arch; then
    _packages=(zram-generator)
    _install_
    sudo tee /etc/systemd/zram-generator.conf << 'EOF'
[zram0]
zram-size = min(ram / 3, 16384)
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now systemd-zram-setup@zram0.service
    zeninf "$finishmsg"
elif is_ubuntu; then
    _packages=(zram-config)
    _install_
    zeninf "$msg036"
elif is_debian; then
    _packages=(zram-tools)
    _install_
    sudo tee /etc/default/zramswap << 'EOF'
ALGO=zstd
PERCENT=50
EOF
    sudo systemctl restart zramswap
    zeninf "$finishmsg"
elif is_fedora; then
    _packages=(zram-generator)
    _install_
    sudo tee /etc/systemd/zram-generator.conf << 'EOF'
[zram0]
zram-size = min(ram / 3, 16384)
EOF
    sudo systemctl daemon-reload   
    sudo systemctl restart swap-create@zram0
    zeninf "$finishmsg"
else
    fatal "$msg077"
fi
