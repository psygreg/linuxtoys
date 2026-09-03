#!/bin/bash
# name: CPU ondemand
# version: 1.0
# description: ondemand_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, ostree, ublue, rhel
# reboot: yes
# nocontainer
# optimized-only: yes
# systemd: yes
# cpu: amd

CPU_VENDOR=$(awk -F ': *' '/^vendor_id/ { print $2; exit }' /proc/cpuinfo)
if [[ "$CPU_VENDOR" != "AuthenticAMD" ]]; then
    die "$hwincompat"
fi

askpass

if [ ! -f /etc/systemd/system/set-ondemand-governor.service ]; then
    if grep -q amd-pstate-epp /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null; then
        prep_create /etc/systemd/system/set-ondemand-governor.service
        sudo tee /etc/systemd/system/set-ondemand-governor.service > /dev/null << 'EOF'
[Unit]
Description=Set CPU governor to ondemand
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do echo balance_performance > "$cpu" 2>/dev/null || true; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
        sysd_enable set-ondemand-governor.service
        echo "Created systemd service to set ondemand governor on boot."
    fi
else
    info "$notdomsg"
    exit 100
fi

info "$rebootmsg"