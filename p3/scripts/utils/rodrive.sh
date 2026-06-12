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
   
   # Ask user to select the OneDrive remote
   REMOTE_NAME=$(zenity --list \
      --title="Select OneDrive Remote" \
      --text="Which remote is your OneDrive?" \
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
      notify-send "OneDrive" "Mounted successfully at $MOUNT_POINT" -i folder-remote
   fi
}

_lang_
display_guide
pkg_install rclone
{ is_ostree && rpm-ostree status --json | grep -q '"state":"staged"' && zenwrn "$msgostreepending" && exit 100; } || true
configure_rclone
mount_drive
zeninf "$msg018"
