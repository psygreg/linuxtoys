#!/bin/bash
# name: lsw
# version: 1.0
# description: lsw_desc
# icon: lsw.svg
# compat: ostree, ublue
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
# podman installation
pdm_install () {
	_packages=(podman podman-compose)
	_install_
	unset _packages
}
# hardware requirements check
hwcheck () {
	# Enforce minimum RAM check
    local total_kb=$(grep MemTotal /proc/meminfo | awk '{ print $2 }')
    local available_kb=$(grep MemAvailable /proc/meminfo | awk '{ print $2 }')
    local total_gb=$(( total_kb / 1024 / 1024 ))
    local available_gb=$(( available_kb / 1024 / 1024 ))
    _cram=$(( total_gb / 3 ))
    if (( _cram < 4 )); then
		nonfatal "Not enough RAM. At least 12GB total is required to continue."
        exit 5
    fi
    # Enforce availability with 1GB buffer (to avoid rounding issues)
    if (( available_gb < (_cram + 1) )); then
		nonfatal "Not enough free RAM. Close some applications and try again."
        exit 5
    fi
    # CPU thread check
    local _total_threads=$(nproc)
    _ccpu=$(( _total_threads / 2 ))
    if (( _ccpu < 2 )); then
		nonfatal "Not enough CPU threads to install Windows hypervisor, minimum 4."
        exit 6
    fi
}
# windows podman container setup
win_install () {
	_packages=(dialog netcat freerdp iproute libnotify)
	_install_
	unset _packages
    sleep 1
    mkdir -p $HOME/.config/winapps
	cd $HOME/.config/winapps
	wget -nc https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/lsw-atom/winapps/compose.yaml
	wget -nc https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/lsw-atom/winapps/winapps.conf
	# make necessary adjustments to compose file
    # Cap at 16GB
    if (( _cram > 16 )); then
        _winram=16
    else
        _winram=$_cram
    fi
    # get cpu threads
    _wincpu="$_ccpu"
    # get C size
    _csize=$(zenity --entry --title="LSW" --text="Enter Windows disk (C:) size in GB. Leave empty to use 50GB."  --entry-text "50" --height=300 --width=300)
    local available_gb=$(df -BG "$HOME/.local" | awk 'NR==2 { gsub("G","",$4); print $4 }')
    if [ -z "$_csize" ]; then
        _winsize="50"
    else
        # stop if input size is not a number
		if [[ -n "$_csize" && ! "$_csize" =~ ^[0-9]+$ ]]; then
			nonfatal "Invalid input for disk size. Please enter a number."
            return 10
        fi
        _winsize="$_csize"
    fi
    if (( _winsize < 40 )); then
		nonfatal "Minimum space to install Windows (C:) is 40GB."
        return 11
    fi
    if (( available_gb < _winsize )); then\
		nonfatal "Not enough disk space: ${_winsize} GB required, ${available_gb} GB available."
        exit 3
    fi
    sed -i "s|^\(\s*RAM_SIZE:\s*\).*|\1\"${_winram}G\"|" compose.yaml
    sed -i "s|^\(\s*CPU_CORES:\s*\).*|\1\"${_wincpu}\"|" compose.yaml
    sed -i "s|^\(\s*DISK_SIZE:\s*\).*|\1\"${_winsize}\"|" compose.yaml
	if command -v konsole &> /dev/null; then
        setsid konsole --noclose -e  "sudo podman-compose --file $HOME/.config/winapps/compose.yaml up" >/dev/null 2>&1 < /dev/null &
	elif command -v ptyxis &> /dev/null; then
		setsid ptyxis -- bash -c "sudo podman-compose --file $HOME/.config/winapps/compose.yaml up; exec bash" >/dev/null 2>&1 < /dev/null &
    elif command -v gnome-terminal &> /dev/null; then
        setsid gnome-terminal -- bash -c "sudo podman-compose --file $HOME/.config/winapps/compose.yaml up; exec bash" >/dev/null 2>&1 < /dev/null &
    else
		nonfatal "No compatible terminal emulator found to launch Podman Compose."
        exit 4
    fi
}
# lsw shortcuts installation
lsw_install () {
	if zenity --question --title "Setup" --text "Is the Windows installation finished?" --height=300 --width=300; then
		wget https://raw.githubusercontent.com/psygreg/linuxtoys-atom/refs/heads/main/lsw-atom/rpmbuild/RPMS/x86_64/lsw-atom-shortcuts-1.1-1.x86_64.rpm
		sudo rpm-ostree install -yA lsw-atom-shortcuts-1.1-1.x86_64.rpm
        rm lsw-atom-shortcuts-1.1-1.x86_64.rpm
		exit 0
	else
		if zenity --question --title "Setup" --text "Do you want to revert all changes? WARNING: This will ERASE all Podman Compose data!" --height=300 --width=360; then
        	sudo podman-compose down --rmi=all --volumes
        	exit 7
		fi
	fi
}
# runtime
hwcheck
sudo_rq
pdm_install
win_install
lsw_install