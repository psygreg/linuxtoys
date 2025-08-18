#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: application-x-executable
# compat: ostree, ublue
# reboot: ostree
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../libs/optimizers.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
# functions
optimizer () {
    if [ ! -f /.autopatch.state ]; then
        # filtered cachyos systemd configs
        wget https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/linuxtoys-cfg-atom/rpmbuild/RPMS/x86_64/linuxtoys-cfg-atom-1.1-1.x86_64.rpm
        sudo rpm-ostree install -yA linuxtoys-cfg-atom-1.1-1.x86_64.rpm
        # shader booster
        local script="shader-patcher-atom" && _invoke_
        # automatic updating
        local AUTOPOLICY="stage"
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
        # install rpmfusion if absent
        if ! rpm -qi "rpmfusion-free-release" &>/dev/null; then
            sudo rpm-ostree install -yA https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
        fi
        if ! rpm -qi "rpmfusion-nonfree-release" &>/dev/null; then
            sudo rpm-ostree install -yA https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
        fi
        # install codecs if absent
        local _packages=("libavcodec-freeworld")
        _install_
        # enable signing of kernel modules (akmods) like Nvidia and VirtualBox
        if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
            if ! rpm -qi "akmods-keys" &>/dev/null; then
                local _packages=(rpmdevtools akmods)
                _install_
                sudo kmodgenca
                sudo mokutil --import /etc/pki/akmods/certs/public_key.der
                git clone https://github.com/CheariX/silverblue-akmods-keys
                cd silverblue-akmods-keys
                sudo bash setup.sh
                sudo rpm-ostree install -yA akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
            fi
        fi
        # fix alive timeout for Gnome
        if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
            dconf write /org/gnome/mutter/check-alive-timeout "20000"
        fi
        # save autopatch state
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/autopatch.state
        sudo mv autopatch.state $HOME/.local/.autopatch.state
    else
        # update configs if already optimized
        cfg_host=$(rpm -qi "linuxtoys-cfg-atom" 2>/dev/null | grep "^Version" | awk '{print $3}')
        cfg_server="1.1"
        if [ "$cfg_host" != "$cfg_server" ]; then
            wget https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/linuxtoys-cfg-atom/rpmbuild/RPMS/x86_64/linuxtoys-cfg-atom-1.1-1.x86_64.rpm
            sudo rpm-ostree remove linuxtoys-cfg-atom
            sudo rpm-ostree install -yA linuxtoys-cfg-atom-1.1-1.x86_64.rpm
        else
            zenity --info --text "$msg281" --height=300 --width=300
        fi
    fi
}
# end messagebox
end_msg () {
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        zenity --info --title "$msg006" --text "$msg268" --height=300 --width=300
        exit 0
    else
        zenity --info --title "$msg006" --text "$msg036" --height=300 --width=300
    fi
}
# menu
while true; do
    CHOICE=$(zenity --list --title="Power Optimizer" \
        --column="$msg229" \
        "Desktop" \
        "Laptop" \
        "$msg070" \
        --height=300 --width=300)

    if [ $? -ne 0 ]; then
        exit 100
   	fi

    case $CHOICE in
    "Desktop") sudo_rq && optimizer && end_msg && break ;;
    "Laptop") sudo_rq && optimizer && psave_lib && end_msg && break ;;
    "$msg070") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done