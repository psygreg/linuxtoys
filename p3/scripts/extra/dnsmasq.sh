#!/bin/bash
# name: DNSMasq
# version: 1.0
# description: dnsmasq_desc
# icon: dnsmasq.svg
# nocontainer
# reboot: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
sudo_rq
dnsmasq_lib
zeninf "$msg036"