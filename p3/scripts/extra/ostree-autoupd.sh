#!/bin/bash
# name: ostree-autoupd
# version: 1.0
# description: ostree-autoupd_desc
# icon: grubtrfs.svg
# compat: ostree, ublue
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
AUTOPOLICY="stage"
prep_edit /etc/rpm-ostreed.conf
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
sysd_enable rpm-ostreed-automatic.timer
sysd_start rpm-ostreed-automatic.timer
unset $AUTOPOLICY
zeninf "$msg018"