#!/bin/bash
# functions

# Create linuxtoys path
LINUXTOYS_HOME="${LINUXTOYS_HOME}"
LINUXTOYS_PROFILE="${LINUXTOYS_PROFILE}"
set_linuxtoys_home()
{
  local _SHELL=$(basename "${SHELL}")
  local UHOME=""
  if id -u $USER > /dev/null 2>&1; then
    UHOME="/home/$USER"
  else
    UHOME="/root"
  fi
  LINUXTOYS_HOME="${UHOME}/.local/share/linuxtoys"
  LINUXTOYS_PROFILE="${LINUXTOYS_HOME}/profile"

  mkdir -p "${LINUXTOYS_HOME}"
  if [ ! -d "${LINUXTOYS_HOME}" ]; then
    printf "\033[1mERROR: An error occurred trying to create the linuxtoys home directory.\033[0m\n"
    exit 1
  else
    touch "${LINUXTOYS_PROFILE}"
    echo "export LINUXTOYS_HOME=\"${LINUXTOYS_HOME}\"" >> "${LINUXTOYS_PROFILE}"
    echo "export LINUXTOYS_PROFILE=\"${LINUXTOYS_PROFILE}\"" >> "${LINUXTOYS_PROFILE}"
    echo ". \"${LINUXTOYS_PROFILE}\"" >> "${UHOME}/.profile"
    echo ". \"${LINUXTOYS_PROFILE}\"" >> "${UHOME}/.${_SHELL}rc"
  fi

  return 0
}
if [ -z "${LINUXTOYS_HOME}" ]; then set_linuxtoys_home; fi

# Set URL backend
UHANDLER="${LINUXTOYS_UHANDLER}"
set_url_handler()
{
  UHANDLER="wget"
  local UHANDLER_FLAGS="-qO-"
  local WGET_NOSSL=0
  if ! wget -q https://www.kernel.org > /dev/null 2>&1 ; then
    WGET_NOSSL=1
    UHANDLER="curl"
    UHANDLER_FLAGS="-s"
  fi

  if [ $WGET_NOSSL -eq 1 ] && ! which curl > /dev/null 2>&1; then
    printf "\033[1mERROR: 'wget' does not have SSL support and '${UHANDLER}' is not installed.\033[0m\n"
    exit 1
  fi

  echo "export LINUXTOYS_UHANDLER=\"${UHANDLER} ${UHANDLER_FLAGS}\"" >> "${LINUXTOYS_HOME}/profile"
  UHANDLER="${UHANDLER} ${UHANDLER_FLAGS}"
  rm index.html

  return 0
}
if [ -z "${UHANDLER}" ]; then set_url_handler; fi

# updater
current_ltver="3.1"
ver_upd () {
    local ver=$(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/ver)
    if [[ "$ver" != "$current_ltver" ]]; then
        if whiptail --title "$msg001" --yesno "$msg002" 8 78; then
            local title="$msg001"
            local msg="$msg157"
            _msgbox_
            xdg-open https://github.com/psygreg/linuxtoys/releases/latest         
        fi
    fi
}

# kernel update checker for debian/ubuntu
krn_chk () {

    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        if [ -f "$HOME/.local/kernelsetting" ]; then
        source $HOME/.local/kernelsetting
            if [ "$_psygreg_krn" == "yes" ]; then
                local _kversion=$(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/psy-krn)
                if [ $(uname -r) != "${_kversion}-psycachy" ] && [ $(uname -r) != "${_kversion}-cachyos" ]; then
                    if whiptail --title "$msg126" --yesno "$msg127" 8 78; then
                        if ! diff -q "$HOME/.local/kernelsetting" <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/kernelsetting-defaults) > /dev/null; then
                            bash <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/src/cachyos-deb.sh) -s
                        else
                            local psycachy_tag=$(${UHANDLER} "https://api.github.com/repos/psygreg/linux-cachyos-deb/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
                            wget "https://github.com/psygreg/linux-cachyos-deb/archive/refs/tags/linux-headers-psycachy_${psycachy_tag}-1_amd64.deb"
                            wget "https://github.com/psygreg/linux-cachyos-deb/archive/refs/tags/linux-image-psycachy_${psycachy_tag}-1_amd64.deb"
                            wget "https://github.com/psygreg/linux-cachyos-deb/archive/refs/tags/linux-libc-dev_${psycachy_tag}-1_amd64.deb"
                            sudo dpkg -i -y linux-image-psycachy_${psycachy_tag}-1_amd64.deb linux-headers-psycachy_${psycachy_tag}-1_amd64.deb linux-libc-dev_${psycachy_tag}-1_amd64.deb
                            sleep 1
                            rm linux-image-psycachy_${psycachy_tag}-1_amd64.deb
                            rm linux-headers-psycachy_${psycachy_tag}-1_amd64.deb
                            if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
                                wget https://raw.githubusercontent.com/psygreg/linux-cachyos-deb/refs/heads/master/secureboot/create-key.sh
                                chmod +x create-key.sh
                                ./create-key.sh --linuxtoys
                            fi
                        fi
                        # clean old kernels
                        dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                        dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
                    fi
                fi
            fi
        fi
    fi

}

# runtime
# check internet connection
# ping google
. /etc/os-release
${UHANDLER} "https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/README.md" > /dev/null || { whiptail --title "Disconnected" --msgbox "LinuxToys requires an internet connection to proceed." 8 78; exit 1; }
# call linuxtoys turbobash lib
source <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
# logger
logfile="$HOME/.local/linuxtoys-log.txt"
_log_
# language and upd checks
_lang_
source <(${UHANDLER} https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
ver_upd
krn_chk

# main menu
while :; do

    CHOICE=$(whiptail --title "LinuxToys" --menu "LinuxToys ${current_ltver}" 25 78 16 \
        "0" "$msg120" \
        "1" "$msg121" \
        "2" "$msg122" \
        "3" "$msg123" \
        "4" "$msg143" \
        "5" "$msg199" \
        "" "" \
        "" "" \
        "6" "$msg124" \
        "7" "GitHub" \
        "8" "$msg059" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        find "$HOME" -maxdepth 1 -type f -name '*supermenu.sh' -exec rm -f {} + && break
    fi

    case $CHOICE in
    0) supmenu="usupermenu" && _invoke_ ;;
    1) supmenu="osupermenu" && _invoke_ ;;
    2) supmenu="gsupermenu" && _invoke_ ;;
    3) supmenu="esupermenu" && _invoke_ ;;
    4) supmenu="dsupermenu" && _invoke_ ;;
    5) supmenu="csupermenu" && _invoke_ ;;
    6) whiptail --title "LinuxToys v${current_ltver}" --msgbox "$msg125" 8 78 ;;
    7) xdg-open https://github.com/psygreg/linuxtoys ;;
    8 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
