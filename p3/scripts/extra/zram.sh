#!/bin/bash
# name: ZRAM/ZSWAP
# description: zram_desc
# icon: preload.svg
# compat: ubuntu, debian, arch, fedora, ostree, rhel
# nocontainer
# new

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_

setup_zram () {
    if is_arch; then
        pkg_install zram-generator
        if [ -f /etc/systemd/zram-generator.conf ]; then
            prep_edit /etc/systemd/zram-generator.conf
        else
            prep_create /etc/systemd/zram-generator.conf
        fi
        sudo tee /etc/systemd/zram-generator.conf << 'EOF'
[zram0]
zram-size = min(ram / 3, 16384)
EOF
        sudo systemctl daemon-reload
        sysd_enable systemd-zram-setup@zram0.service
        sysd_start systemd-zram-setup@zram0.service
    elif is_ubuntu; then
        pkg_install zram-config
    elif is_debian; then
        pkg_install zram-tools
        if [ -f /etc/default/zramswap ]; then
            prep_edit /etc/default/zramswap
        else
            prep_create /etc/default/zramswap
        fi
        sudo tee /etc/default/zramswap << 'EOF'
ALGO=zstd
PERCENT=50
EOF
        sysd_stop zramswap
        sysd_start zramswap
    else
        zenwrn "$msg234"
        exit 100
    fi
}

_total_ram_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
if [ "$_total_ram_kb" -gt 16777216 ] && ! is_rhel; then
    setup_zram
else
    zswap_lib
    zenwrn "$zswapmsg"
fi
zeninf "$finishmsg"