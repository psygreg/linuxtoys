#!/bin/bash
# TODO fix, someday
if grep -qi "slowroll" /etc/os-release; then
    sudo zypper addrepo https://download.opensuse.org/repositories/home:runa-chin/openSUSE_Slowroll/home:runa-chin.repo && sudo zypper ref
else
    sudo zypper addrepo https://download.opensuse.org/repositories/home:runa-chin/openSUSE_Tumbleweed/home:runa-chin.repo && sudo zypper ref
fi
sudo zypper in grubby -y
sudo grubby --update-kernel="/boot/vmlinuz-$(uname -r)" --args="psi=1"