#!/bin/bash
# source lib and langfiles
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# updater
if whiptail --title "$msg126" --yesno "$msg127" 8 78; then
    if [ -f "$HOME/.local/kernelsetting-lts" ]; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/psycachy/psycachy-install.sh) --lts
    elif [ -f "$HOME/.local/kernelsetting" ]; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/psycachy/psycachy-install.sh) --std
    fi
    # update systemd settings
    cachyos_sysd_lib
    exit 0
else
    exit 0
fi
