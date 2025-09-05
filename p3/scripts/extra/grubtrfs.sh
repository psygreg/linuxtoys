#!/bin/bash
# name: GRUB-btrfs
# version: 1.0
# description: grubtrfs_desc
# icon: grubtrfs.svg
# compat: ubuntu, debian, arch, fedora, suse
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# functions
# check dependencies
dep_check () {
    if ! dpkg -l | grep -q grub-efi; then
        nonfatal $"No GRUB found."
        exit 1
    else
        _packages=()
        if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
            _packages=(gawk inotify-tools make)
        elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            _packages=(gawk inotify-tools)
        elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
            _packages=(gawk inotify-tools make)
        fi
        _install_
    fi
}
# install grub-btrfs and set up automatic snapshot listing
grubtrfs_in () {
    if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
        insta snapper
        sudo btrfs subvolume delete -R /.snapshots
        sudo snapper -c root create-config /
        sudo snapper -c root create --command dnf
    elif [[ "$ID_LIKE" == *suse* ]]; then
        insta snapper
        sudo btrfs subvolume delete -R /.snapshots
        sudo snapper -c root create-config /
        sudo snapper -c root create --command zypper
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        insta snapper
        sudo btrfs subvolume delete -R /.snapshots
        sudo snapper -c root create-config /
        sudo snapper -c root create --command pacman
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        insta snapper
        sudo btrfs subvolume delete -R /.snapshots
        sudo snapper -c root create-config /
        sudo snapper -c root create --command apt
    fi
    sleep 1
    sudo sed -i 's/^TIMELINE_CREATE=.*/TIMELINE_CREATE="no"/' '/etc/snapper/configs/root'
    sudo sed -i 's/^NUMBER_LIMIT=.*/NUMBER_LIMIT="5"/' '/etc/snapper/configs/root'
    sudo sed -i 's/^NUMBER_LIMIT_IMPORTANT=.*/NUMBER_LIMIT_IMPORTANT="5"/' '/etc/snapper/configs/root'
    sudo sed -i 's/^NUMBER_CLEANUP=.*/NUMBER_CLEANUP="yes"/' '/etc/snapper/configs/root'
    sudo sed -i 's/^EMPTY_PRE_POST_CLEANUP=.*/EMPTY_PRE_POST_CLEANUP="yes"/' '/etc/snapper/configs/root'
    sudo systemctl enable snapper-boot.timer
    sudo systemctl enable snapper-cleanup.timer
    sudo systemctl start snapper-cleanup.timer
    if [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ (arch) ]]; then
        insta grub-btrfs
    else
        cd $HOME
        git clone https://github.com/Antynea/grub-btrfs.git
        cd grub-btrfs
        sudo make install
    fi
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]] || [[ "$ID" =~ (fedora|suse) ]]; then
        sudo sed -i 's|^GRUB_BTRFS_MKCONFIG=.*|GRUB_BTRFS_MKCONFIG=/sbin/grub2-mkconfig|' '/etc/default/grub-btrfs/config'
        sudo sed -i 's|^GRUB_BTRFS_GRUB_DIRNAME=.*|GRUB_BTRFS_GRUB_DIRNAME="/boot/grub2"|' '/etc/default/grub-btrfs/config'
        sudo sed -i 's|^GRUB_BTRFS_SCRIPT_CHECK=.*|GRUB_BTRFS_SCRIPT_CHECK=grub2-script-check|' '/etc/default/grub-btrfs/config'
        sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [ "$ID" == "debian" ]; then
        sudo update-grub
    fi
    sudo systemctl enable --now grub-btrfsd
}
# runtime
if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
    if zenity --question --title="Grub-Btrfs Installer" --text=$"This will list snapshots in your GRUB. It will only work if your root filesystem is btrfs. Proceed?" --width 360 --height 300; then
        sudo_rq
        dep_check
        grubtrfs_in
        zeninf $"Installation successful."
    fi
else
    nonfatal $"Your root filesystem is not btrfs."
fi