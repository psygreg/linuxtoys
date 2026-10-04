#!/usr/bin/env bash
# name: Homebrew
# description: brew_desc
# icon: brew.png
# repo: https://brew.sh/

if ! brew_bin=$(_brew_executable); then
    askpass || exit 1
    brew_installer=$(mktemp) || exit 1
    trap 'rm -f "$brew_installer"' EXIT
    curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$brew_installer" \
        || die "Failed to download the Homebrew installer"
    NONINTERACTIVE=1 /bin/bash "$brew_installer" || die "Failed to install Homebrew"
    brew_bin=$(_brew_executable) || die "Homebrew is unavailable after installation"
    brew_prefix=$("$brew_bin" --prefix) || die "Unable to determine Homebrew prefix"
    brew_prefix64=$(printf '%s' "$brew_prefix" | base64 | tr -d '\n')
    _append_transmap "homebrew-manager $brew_prefix64"
    if [ -f "$HOME/.bashrc" ]; then
        prep_edit "$HOME/.bashrc"
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
    fi
    if [ -f "$HOME/.zshrc" ]; then
        prep_edit "$HOME/.zshrc"
        echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.zshrc
    fi
    if [ -f "$HOME/.config/fish/config.fish" ]; then
        prep_edit "$HOME/.config/fish/config.fish"
        echo 'brew shellenv | source' >> "$HOME/.config/fish/config.fish"
    fi
fi
_brew_source_changed
info "$finishmsg"
