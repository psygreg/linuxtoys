#!/bin/bash
# name: Zash Terminal
# version: 1.0
# description: zash_desc
# icon: zashterminal.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# repo: https://github.com/leoberbert/zashterminal
# revert: arch, cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

install_url="https://raw.githubusercontent.com/leoberbert/zashterminal/refs/heads/main/install.sh"
tmp_installer="/tmp/zashterminal-install.sh"

sudo_rq_local() {
    if [[ "${DISABLE_ZENITY:-0}" != "1" ]] && command -v zenity >/dev/null 2>&1; then
        local max_attempts=3
        local attempts=0
        local pass

        while (( attempts < max_attempts )); do
            pass=$(zenity --password --title="LinuxToys - Zash Terminal")
            [ $? -ne 0 ] && fatal "Installation cancelled by user."

            if echo "$pass" | sudo -S -v >/dev/null 2>&1; then
                return 0
            fi

            attempts=$((attempts + 1))
            zenity --error --title="Authentication failed" --text="Wrong password. Attempts: ${attempts}/${max_attempts}" --width=360 --height=220
        done

        fatal "Wrong password or sudo failed (max attempts reached)."
    fi

    sudo_rq
}

open_zashterminal_now() {
    if command -v zashterminal >/dev/null 2>&1; then
        nohup zashterminal >/dev/null 2>&1 &
        sleep 1
        return 0
    fi

    if command -v gtk-launch >/dev/null 2>&1; then
        nohup gtk-launch org.leoberbert.zashterminal >/dev/null 2>&1 &
        sleep 1
        return 0
    fi

    return 1
}

sudo_rq_local

if is_arch || is_cachy; then
    pkg_install zashterminal
else
    if ! curl -fsSL "$install_url" -o "$tmp_installer"; then
        fatal "Failed to download Zashterminal installer."
    fi
    chmod +x "$tmp_installer"
    if ! bash "$tmp_installer"; then
        rm -f "$tmp_installer"
        fatal "Zashterminal installation failed."
    fi
    rm -f "$tmp_installer"
fi

zeninf "Zashterminal installation completed."
if [[ "${DISABLE_ZENITY:-0}" != "1" ]] && command -v zenity >/dev/null 2>&1; then
    if zenity --question --title="Zash Terminal" --text="Zash Terminal was installed successfully.\n\nDo you want to open it now?" --ok-label="Open" --cancel-label="Exit" --width=420 --height=260; then
        if ! open_zashterminal_now; then
            zenity --warning --title="Zash Terminal" --text="Could not auto-launch Zash Terminal. You can open it manually from the app menu." --width=460 --height=260
        fi
    fi
else
    read -r -p "Open Zash Terminal now? [y/N]: " _open_now
    if [[ "$_open_now" =~ ^[Yy]$ ]]; then
        if ! open_zashterminal_now; then
            echo "Could not auto-launch Zash Terminal. Open it manually from the app menu."
        fi
    fi
fi
exit 0
