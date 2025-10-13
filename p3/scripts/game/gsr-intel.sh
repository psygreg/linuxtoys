#!/bin/bash
# name: GPU Screen Recorder
# version: 1.0
# description: gsr_desc
# icon: gsr.png
# gpu: Intel
# repo: https://git.dec05eba.com/?p=about
# nocontainer
# negates: gsr

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# intel quicksync support requires native package
sudo_rq
if is_fedora; then
    sudo dnf copr enable brycensranch/gpu-screen-recorder-git
    _packages=(gpu-screen-recorder-ui libva-intel-media-driver)
elif is_ostree; then
    wget "https://copr.fedorainfracloud.org/coprs/brycensranch/gpu-screen-recorder-git/repo/fedora-$(rpm -E %fedora)/brycensranch-gpu-screen-recorder-git-fedora-$(rpm -E %fedora).repo"
    sudo install -o 0 -g 0 "brycensranch-gpu-screen-recorder-git-fedora-$(rpm -E %fedora).repo" "/etc/yum.repos.d/brycensranch-gpu-screen-recorder-git-fedora-$(rpm -E %fedora).repo"
    rm "brycensranch-gpu-screen-recorder-git-fedora-$(rpm -E %fedora).repo"
    _packages=(gpu-screen-recorder-ui libva-intel-media-driver)
elif is_suse; then
    _packages=(gpu-screen-recorder intel-media-driver)
elif is_debian || is_ubuntu; then
    sudo bash -c "$(wget -q https://pacstall.dev/q/install -O -)"
    pacstall -I gpu-screen-recorder
    _packages=(intel-media-driver)
elif is_arch || is_cachy; then
    git clone https://aur.archlinux.org/gpu-screen-recorder.git
    cd gpu-screen-recorder || exit 1
    makepkg -d
    sudo pacman -U --noconfirm gpu-screen-recorder-*.tar.zst
    cd ..
    rm -rf gpu-screen-recorder
    _packages+=(libva-intel-driver intel-media-driver)
fi    
_install_
zeninf "$msg018"