#!/bin/bash
# name: ostree-autoupd
# version: 1.0
# description: ostree-autoupd_desc
# icon: grubtrfs.svg
# compat: ostree, ublue
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
sudo_rq
AUTOPOLICY="stage"
sudo cp /etc/rpm-ostreed.conf /etc/rpm-ostreed.conf.bak
if grep -q "^AutomaticUpdatePolicy=" /etc/rpm-ostreed.conf; then
    sudo sed -i "s/^AutomaticUpdatePolicy=.*/AutomaticUpdatePolicy=${AUTOPOLICY}/" /etc/rpm-ostreed.conf
else
    sudo awk -v policy="$AUTOPOLICY" '
    /^\[Daemon\]/ {
        print
        print "AutomaticUpdatePolicy=" policy
        next
    }
    { print }
    ' /etc/rpm-ostreed.conf | sudo tee /etc/rpm-ostreed.conf > /dev/null
fi
echo "AutomaticUpdatePolicy set to: $AUTOPOLICY"
sudo systemctl enable rpm-ostreed-automatic.timer --now
unset $AUTOPOLICY
zeninf "$msg018"