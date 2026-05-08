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

get_credentials() {
   CLIENT_ID=$(zenity --entry \
      --title="OneDrive Configuration" \
      --text="Enter your Azure App Client ID:" \
      --width=400)  
   if [ -z "$CLIENT_ID" ]; then
      fatal "Client ID cannot be empty"
   fi
    
   CLIENT_SECRET=$(zenity --password \
      --title="OneDrive Configuration" \
      --text="Enter your Azure App Client Secret:")
    
   if [ -z "$CLIENT_SECRET" ]; then
      fatal "Client Secret cannot be empty"
   fi
}

configure_rclone() {
   (
      echo "n"                   # New remote
      echo "$REMOTE_NAME"        # Remote name
      echo "onedrive"            # OneDrive service
      echo "$CLIENT_ID"          # Client ID
      echo "$CLIENT_SECRET"      # Client Secret
      echo ""                    # Skip region (use default)
      echo "n"                   # Edit advanced config: No
      echo "y"                   # Use auto config: Yes
      sleep 2
      echo "y"                   # Confirm
      echo "q"                   # Quit
   ) | rclone config
    
   if [ $? -eq 0 ]; then
      zeninf "Rclone configured successfully with the provided credentials."
      # Update REMOTE_NAME for mounting
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
get_credentials
configure_rclone
mount_drive
zeninf "$msg018"
