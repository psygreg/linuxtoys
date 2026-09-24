#!/usr/bin/env bash

if is_ubuntu || is_debian; then
    # compat check
    is_ubuntu && case "$UBUNTU_CODENAME" in
        resolute|stonking) ;;
        *) die "$incompatmsg" ;;
    esac
    is_debian && {
        debian_version="$(cat /etc/debian_version 2>/dev/null)" || die "$incompatmsg"
        case "$debian_version" in
            sid|*/sid|testing|*/testing) ;;
            *) dpkg --compare-versions "$debian_version" ge 13 2>/dev/null || die "$incompatmsg" ;;
        esac
    }
    # repository installation
    prep_create /etc/apt/sources.list.d/punktfunk.list
    sudo_ install -d -m 0755 /etc/apt/keyrings
    curl -fsSL https://git.unom.io/api/packages/unom/debian/repository.key | sudo_ tee /etc/apt/keyrings/punktfunk.asc >/dev/null
    echo "deb [signed-by=/etc/apt/keyrings/punktfunk.asc] https://git.unom.io/api/packages/unom/debian stable main" | sudo_ tee /etc/apt/sources.list.d/punktfunk.list
    sudo_ apt update
elif is_fedora; then
    # set repository naming
    fedora_version="$(rpm -E %fedora 2>/dev/null)"
    if [[ "$fedora_version" =~ ^[0-9]+$ ]] && (( fedora_version >= 44 )); then
        punktfunk_repo="fedora-44"
    elif [ "$fedora_version" = 43 ]; then
        punktfunk_repo="bazzite"
    else
        die "$incompatmsg"
    fi
    # repository installation
    prep_create /etc/yum.repos.d/punktfunk.repo
    sudo tee /etc/yum.repos.d/punktfunk.repo >/dev/null <<REPO
[punktfunk]
name=punktfunk
baseurl=https://git.unom.io/api/packages/unom/rpm/$punktfunk_repo
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://git.unom.io/api/packages/unom/rpm/repository.key
       https://git.unom.io/api/packages/unom/generic/punktfunk-keys/1/RPM-GPG-KEY-punktfunk
REPO
elif is_arch || is_cachy; then
    # repository installation
    curl -fsS https://git.unom.io/api/packages/unom/arch/repository.key | sudo_ pacman-key --add -
    sudo_ pacman-key --lsign-key E0CA04465C99C936E0B0C6510A317015A34DDD69
    prep_edit /etc/pacman.conf
    grep -q '^\[punktfunk\]' /etc/pacman.conf || printf '\n[punktfunk]\nServer = https://git.unom.io/api/packages/unom/arch/$repo/$arch\n' | sudo_ tee -a /etc/pacman.conf >/dev/null
    sudo_ pacman -Sy
fi
