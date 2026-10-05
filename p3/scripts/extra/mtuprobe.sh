#!/usr/bin/env bash
# name: mtuprobe
# description: mtuprobe_desc
# icon: bbr.svg
# compat: !steamos, !ostree, !cachy
# nocontainer
# systemd: yes

askpass
prep_create /usr/lib/sysctl.d/99-mtuprobe.conf

cat <<'EOF' | sudo_ tee /usr/lib/sysctl.d/99-mtuprobe.conf >/dev/null
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_base_mss = 1024
EOF

sudo_ sysctl -p /usr/lib/sysctl.d/99-mtuprobe.conf || die "Failed to enable MTU probing"
sudo_ sysctl --system || die "Failed to refresh sysctl"

info "$finishmsg"
