#!/bin/bash
# name: DNSMasq
# version: 1.0
# description: dnsmasq_desc
# icon: dnsmasq.svg
# nocontainer
# reboot: yes
# repo: https://thekelleys.org.uk/gitweb/?p=dnsmasq.git

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
dnsmasq_lib
zeninf "$msg036"