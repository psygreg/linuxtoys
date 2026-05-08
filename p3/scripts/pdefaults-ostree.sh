#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ostree, ublue
# reboot: ostree
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
# functions
optimizer () {
    cd $HOME
    if [ ! -f $HOME/.local/.autopatch.state ]; then
        # shader booster
        sboost_lib
        # automatic updating
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
        # install rpmfusion if absent
        if ! rpm -qi "rpmfusion-free-release" &>/dev/null; then
            sudo rpm-ostree install -yA https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
        fi
        if ! rpm -qi "rpmfusion-nonfree-release" &>/dev/null; then
            sudo rpm-ostree install -yA https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
        fi
        # enable signing of kernel modules (akmods) like Nvidia and VirtualBox
        if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
            if ! rpm -qi "akmods-keys" &>/dev/null; then
                pkg_install rpmdevtools akmods
                sudo kmodgenca
                sudo mokutil --import /etc/pki/akmods/certs/public_key.der
                prep_tmp
                git clone https://github.com/CheariX/silverblue-akmods-keys
                cd silverblue-akmods-keys
                sudo bash setup.sh
                pkg_fromfile akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
            fi
        fi
        # fix alive timeout for Gnome
        if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
            sudo gsettings set org.gnome.mutter check-alive-timeout 20000
        fi
        # fix GTK app rendering for Intel BMG and Nvidia GPUs
        fix_intel_gtk
        # full kernel preemption for better latency
        preempt_lib
        # save autopatch state
        touch "$HOME/.local/.autopatch.state"
    else
        zenwrn "$msg234"
        exit 100
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
        "Install without Power Profile" \
        "Desktop" \
        "Laptop" \
        "$msg070" \
        --height=360 --width=360)

    if [ $? -ne 0 ]; then
        exit 100
   	fi

    case $CHOICE in
    "Install without Power Profile" ) sudo_rq && optimizer && end_msg && break ;;
    "Desktop") sudo_rq && pp_ondemand && optimizer && end_msg && break ;;
    "Laptop") sudo_rq && optimizer && psave_lib && end_msg && break ;;
    "$msg070") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done
