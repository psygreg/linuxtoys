#!/bin/bash
# name: RClone OneDrive
# description: rodrive_desc
# icon: rodrive.svg
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"

REMOTE_NAME="OneDrive"
MOUNT_POINT="$HOME/OneDrive"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/onedrive.desktop"
RCLONE_CONFIG_DIR="$HOME/.config/rclone"

display_guide() {
   echo "$odrive_guide_text" | zenity --text-info \
      --title="RClone OneDrive Setup" \
      --text="$odrive_guide_text" \
      --width=700 \
      --height=600 \
      --no-wrap
   
   if [ $? -ne 0 ]; then
      echo "Setup cancelled by user"
      exit 100
   fi
}

configure_rclone() {
   rclone config
    
   if [ $? -eq 0 ]; then
      zeninf "Rclone configured successfully."
      REMOTE_NAME=$(zenity --entry \
         --title="Remote Name" \
         --text="What did you name your OneDrive remote?" \
         --entry-text="OneDrive")
      
      if [ -z "$REMOTE_NAME" ]; then
         fatal "Remote name cannot be empty"
      fi
      REMOTE_NAME="${REMOTE_NAME}:"
   else
      fatal "Rclone configuration failed"
   fi
}

mount_drive() {
   prep_dir "$MOUNT_POINT"
   rclone_mount "$REMOTE_NAME" "$MOUNT_POINT"
   
   if command -v notify-send &> /dev/null; then
      notify-send "OneDrive" "Mounted successfully at $MOUNT_POINT" -i folder-remote
   fi
}

_lang_
display_guide
pkg_install rclone
if is_ostree; then
   if rpm-ostree status --json | grep -q '"live-replaced": true'; then
      zeninf "Please reboot and run this script again to complete the configuration." # TODO: add translation
      exit 0
   fi
fi
configure_rclone
mount_drive
zeninf "$msg018"
