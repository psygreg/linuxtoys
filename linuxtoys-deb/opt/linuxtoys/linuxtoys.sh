#!/bin/bash
# functions

# enable flatpaks (for Ubuntu and flavours)
flatpak_in () {

    # ask confirmation before proceeding
    if whiptail --title "Enabling Flatpaks" --yesno "This will enable Flatpaks and add the Flathub source to your system. Proceed?" 8 78; then
        # installation
        sudo apt install flatpak
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo --system
        # notify that a reboot is required to enable flatpaks
        whiptail --title "Flatpaks Enabled" --msgbox "Reboot to add it to PATH and show apps in the menu." 8 78
    fi

}

# install gnome-software and plugins
gsoftware_in () {

    # ask confirmation before proceeding
    if whiptail --title "Installing Gnome Software" --yesno "This will install the Software app (and necessary plugins) as apt and flatpak front-end. Proceed?" 8 78; then
        # installation
        sudo apt install gnome-software gnome-software-plugin-flatpak gnome-software-plugin-snap
        # confirm completion
        whiptail --title "Gnome Software Installed" --msgbox "Installation successful." 8 78
    fi

}

# fetch and patch shader cache using shader-booster
booster_in () {

    if whiptail --title "Shader Booster" --yesno "This will patch your shader cache size, fixing stutters in many games. Proceed?" 8 78; then
        # patching
        if [ ! -f “patcher.sh” ]; then
            wget https://github.com/psygreg/shader-booster/releases/latest/download/patcher.sh
            chmod +x patcher.sh
        fi
        ./patcher.sh
    fi

}

# download and properly install FireAlpaca as a .deb package
firealpaca_in () {

    if whiptail --title "FireAlpaca Installer" --yesno "This will install FireAlpaca from a deb package created from the original AppImage. Proceed?" 8 78; then
        # patching
        if [ ! -f “installer.sh” ]; then
            wget https://github.com/psygreg/firealpaca-deb/releases/latest/download/installer.sh
            chmod +x installer.sh
        fi
        ./installer.sh
    fi


}

# install linux-cachyos optimized kernel
kernel_in () {

    if whiptail --title "CachyOS Custom Kernel Installer" --yesno "This will open the menu to set up a custom kernel from linux-cachyos patches. Proceed?" 8 78; then
        # patching
        if [ ! -f “patcher.sh” ]; then
            wget -O cachyos-deb.sh https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/cachyos-deb.sh
            chmod +x cachyos-deb.sh
        fi
        ./cachyos-deb.sh
    fi

}

# install ROCm for AMD GPU computing
rocm_in () {

    whiptail --title "ROCm Installer" --msgbox "This will install ROCm in your system, and is ONLY meant for AMD graphics cards, RDNA 2 or newer." 8 78
    if whiptail --title "ROCm Installer" --yesno "This may not work outside Ubuntu and its flavours. Proceed?" 8 78; then
        sudo apt install libamd-comgr2 libhsa-runtime64-1 librccl1 librocalution0 librocblas0 librocfft0 librocm-smi64-1 librocsolver0 librocsparse0 rocm-device-libs-17 rocm-smi rocminfo hipcc libhiprand1 libhiprtc-builtins5 radeontop rocm-opencl-icd ocl-icd-libopencl1 clinfo 
        sudo usermod -aG render,video $USER
        whiptail --title "ROCm Installer" --msgbox "Installation complete. Reboot to apply changes."
    fi

}

# main menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "Choose an option" 25 78 16 \
        "0" "Set up Flathub" \
        "1" "Set up Gnome Software" \
        "2" "Apply Shader Booster" \
        "3" "Install or update FireAlpaca" \
        "4" "Install or update linux-cachyos Kernel" \
        "5" "Install ROCm for AMD GPUs" \
        "6" "Exit" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) flatpak_in ;;
    1) gsoftware_in ;;
    2) booster_in ;;
    3) firealpaca_in ;;
    4) kernel_in ;;
    5) rocm_in ;;
    6 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done

