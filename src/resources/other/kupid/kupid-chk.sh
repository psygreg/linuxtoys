#!/bin/bash
. /etc/os-release
releases=$(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases")
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    if [ -f "$HOME/.local/kernelsetting" ]; then
        source $HOME/.local/kernelsetting
        if [ "$_psygreg_krn" == "yes" ]; then
            std_tag=$(echo "$releases" | jq -r '.[].tag_name' | grep -i '^STD-' | sort -Vr | head -n 1)
            kver_std="${std_tag#STD-}"
            if [ $(uname -r) != "${kver_std}-psycachy" ] && [ $(uname -r) != "${kver_std}-cachyos" ]; then
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
    elif [ -f "$HOME/.local/kernelsetting-lts" ]; then
        lts_tag=$(echo "$releases" | jq -r '.[].tag_name' | grep -i '^LTS-' | sort -Vr | head -n 1)
        kver_lts="${lts_tag#LTS-}"
        if [ $(uname -r) != "${kver_lts}-psycachy-lts" ]; then
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
