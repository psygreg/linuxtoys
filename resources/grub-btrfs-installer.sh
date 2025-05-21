#!/bin/bash
# functions

# check dependencies
dep_check () {

    local dependencies=()
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]]; then
        dependencies=(newt btrfs-progs grub2 bash gawk inotify-tools)
    elif [ "$ID" == "arch" ]; then
        dependencies=(libnewt btrfs-progs grub bash gawk inotify-tools)
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]]; then
        dependencies=(whiptail btrfs-progs grub bash gawk inotify-tools)
    fi

}

# install grub-btrfs and set up automatic snapshot listing
grubtrfs_in () {

    cd $HOME
    git clone https://github.com/Antynea/grub-btrfs.git
    cd grub-btrfs
    make install
    if [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]]; then
        sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    elif [ "$ID" == "arch" ]; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg
    elif [[ "$ID_LIKE" =~ (ubuntu|debian) ]]; then
        sudo update-grub
    fi
    sudo systemctl enable grub-btrfsd
    sudo systemctl start grub-btrfsd

}

# runtime
. /etc/os-release
dep_check
if whiptail --title "Grub-Btrfs Installer" --yesno "This will list snapshots in your GRUB. It will only work if your root filesystem is btrfs. Proceed?" 8 78; then
    grubtrfs_in
    whiptail --title "Grub-Btrfs Installer" --msgbox "Installation successful."
    cd ..
    rm -rf grub-btrfs
    exit 0
fi