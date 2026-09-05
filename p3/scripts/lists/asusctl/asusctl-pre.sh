#!/bin/bash

if is_fedora && [[ ! $ID =~ ^(ultramarine|nobara)$ ]]; then
    call_script terra
elif is_arch; then
    askpass
    sudo bash -c 'grep -q ^\[ogc\] /etc/pacman.conf || cat <<EOF >>/etc/pacman.conf
[ogc]
Server = https://pacman.opengamingcollective.org
EOF'
    sudo pacman-key --recv-keys F79100EF8C802DAB81C323BB8EEA5962FE510E19
    sudo pacman-key --lsign-key F79100EF8C802DAB81C323BB8EEA5962FE510E19
fi