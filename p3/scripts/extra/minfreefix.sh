#!/bin/bash
# name: minfreefix
# version: 1.0
# description: minfreefix_desc
# icon: preload.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, rhel
# optimized-only: yes
# systemd: yes
# reboot: yes

askpass

cat << 'EOF' | sudo tee "/etc/systemd/system/set-min-free-mem.service" > /dev/null
[Unit]
Description=Set vm.min_free_kbytes dynamically
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "sysctl -w vm.min_free_kbytes=$(awk '/MemTotal/ {printf \"%.0f\", $2 * 0.01}' /proc/meminfo)"

[Install]
WantedBy=sysinit.target
EOF

sudo chmod 644 "/etc/systemd/system/set-min-free-mem.service"
sudo systemctl daemon-reload
sysd_enable set-min-free-mem.service

info "$rebootmsg" # while immediate rebooting is not necessary it is ideal