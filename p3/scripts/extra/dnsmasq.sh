#!/bin/bash
# name: DNSMasq
# version: 1.0
# description: dnsmasq_desc
# icon: dnsmasq.svg
# nocontainer
# reboot: yes
# repo: https://thekelleys.org.uk/gitweb/?p=dnsmasq.git
# compat: !rhel

askpass

pkg_install dnsmasq
if is_debian; then
    pkg_install resolvconf
fi

if [ -f /etc/dnsmasq.conf ]; then
    prep_edit /etc/dnsmasq.conf
    sudo sed -i 's/^#\s*domain-needed/domain-needed/' /etc/dnsmasq.conf
    sudo sed -i 's/^#\s*bogus-priv/bogus-priv/' /etc/dnsmasq.conf
    if grep -Eq '^[#[:space:]]*cache-size=' /etc/dnsmasq.conf; then
        sudo sed -i 's/^[#[:space:]]*cache-size=.*/cache-size=10000/' /etc/dnsmasq.conf
    else
        echo 'cache-size=10000' | sudo tee -a /etc/dnsmasq.conf >/dev/null
    fi
fi

sysd_enable dnsmasq

info "$rebootmsg"