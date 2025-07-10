#!/bin/bash
. /etc/os-release
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    if [ -f "$HOME/.local/kernelsetting" ]; then
        source $HOME/.local/kernelsetting
        if [ "$_psygreg_krn" == "yes" ]; then
            local _kversion=$(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/psy-krn)
            if [ $(uname -r) != "${_kversion}-psycachy" ] && [ $(uname -r) != "${_kversion}-cachyos" ]; then
                if ! diff -q "$HOME/.local/kernelsetting" <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/kernelsetting-defaults) > /dev/null; then
                    exit 1
                else
                    cd $HOME/.local/kupid
                    if command -v konsole &> /dev/null; then
                        setsid konsole --noclose -e bash -c "./kupid-upd.sh" >/dev/null 2>&1 < /dev/null &
                    elif command -v gnome-terminal &> /dev/null; then
                        setsid gnome-terminal -- bash -c "./kupid-upd.sh" >/dev/null 2>&1 < /dev/null &
                    elif command -v xfce4-terminal &> /dev/null; then
                        setsid xfce4-terminal --hold -e "bash -c './kupid-upd.sh'" >/dev/null 2>&1 < /dev/null &
                    else
                        exit 2
                    fi
                    sleep 10
                    exit 0
                fi
            fi
        fi
    fi
fi
