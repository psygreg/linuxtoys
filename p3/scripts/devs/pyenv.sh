#!/bin/bash
# name: PyEnv
# version: 1.0
# description: pyenv_desc
# icon: python.svg
# repo: https://github.com/pyenv

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian || is_ubuntu; then
    pkg_install make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
elif is_arch || is_cachy; then
    pkg_install base-devel openssl zlib xz tk
elif is_fedora; then
    pkg_install make gcc patch zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel libuuid-devel gdbm-libs libnsl2
elif is_suse; then
    pkg_install gcc automake bzip2 libbz2-devel xz xz-devel openssl-devel ncurses-devel readline-devel zlib-devel tk-devel libffi-devel sqlite3-devel gdbm-devel make findutils patch
fi
# pyenv installation and addition to PATH
prep_dir "$HOME/.pyenv"
curl -fsSL https://pyenv.run | bash
if [[ -f "${HOME}/.bash_profile" ]]; then
    prep_edit "$HOME/.bash_profile"
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init - bash)"' >> ~/.bash_profile
elif [[ -f "$HOME/.profile" ]]; then
    prep_edit "$HOME/.profile"
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
    echo 'eval "$(pyenv init - bash)"' >> ~/.profile
fi
if [[ -f "$HOME/.zshrc" ]]; then
    prep_edit "$HOME/.zshrc"
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
    echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc
fi
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
prep_edit "$HOME/.bashrc"
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
# basic usage instruction prompt
zeninf "$msg135"
xdg-open https://github.com/pyenv/pyenv?tab=readme-ov-file#usage
xdg-open https://github.com/pyenv/pyenv-virtualenv?tab=readme-ov-file#usage