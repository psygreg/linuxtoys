#!/bin/bash
# name: RClone Google Drive
# description: rgdrive_desc
# icon: rgdrive.svg

source "$SCRIPT_DIR/libs/linuxtoys.lib"

REMOTE_NAME="GoogleDrive"
MOUNT_POINT="$HOME/GoogleDrive"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/google_drive.desktop"
RCLONE_CONFIG_DIR="$HOME/.config/rclone"

display_guide() {
   echo "$gdrive_guide_text" | zenity --text-info \
      --title="RClone Google Drive Setup" \
      --text="$gdrive_guide_text" \
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
    
   # Get list of configured remotes
   REMOTES=$(rclone listremotes)
   
   if [ -z "$REMOTES" ]; then
      fatal "No remotes configured. Please configure a remote using 'rclone config' first."
   fi
   
   # Convert remotes to array for zenity
   REMOTE_ARRAY=()
   while IFS= read -r remote; do
      REMOTE_ARRAY+=("$remote")
   done <<< "$REMOTES"
   
   # Ask user to select the Google Drive remote
   REMOTE_NAME=$(zenity --list \
      --title="Select Google Drive Remote" \
      --text="Which remote is your Google Drive?" \
      --column="Remotes" \
      "${REMOTE_ARRAY[@]}")
   
   if [ -z "$REMOTE_NAME" ]; then
      fatal "No remote selected"
   fi
   
   zeninf "Using remote: $REMOTE_NAME"
}
mount_drive() {
   prep_dir "$MOUNT_POINT"
   rclone_mount "$REMOTE_NAME" "$MOUNT_POINT"
   
   if command -v notify-send &> /dev/null; then
      notify-send "Google Drive" "Mounted successfully at $MOUNT_POINT" -i folder-remote
   fi
}

_lang_
display_guide
pkg_install --ostreecheck rclone
configure_rclone
mount_drive
zeninf "$msg018"