#!/bin/bash
# name: RClone Google Drive
# description: rgdrive_desc
# icon: rgdrive.svg
# new

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

get_credentials() {
   CLIENT_ID=$(zenity --entry \
      --title="Google Drive Configuration" \
      --text="Enter your Google Cloud Client ID:" \
      --width=400)  
   if [ -z "$CLIENT_ID" ]; then
      fatal "Client ID cannot be empty"
   fi
    
   CLIENT_SECRET=$(zenity --password \
      --title="Google Drive Configuration" \
      --text="Enter your Google Cloud Client Secret:")
    
   if [ -z "$CLIENT_SECRET" ]; then
      fatal "Client Secret cannot be empty"
   fi
}
configure_rclone() {
   (
      echo "n"                   # New remote
      echo "$REMOTE_NAME"        # Remote name
      echo "drive"               # Google Drive service
      echo "$CLIENT_ID"          # Client ID
      echo "$CLIENT_SECRET"      # Client Secret
      echo "1"                   # Scope: full access
      echo ""                    # Skip service_account_file
      echo "n"                   # Edit advanced config: No
      echo "y"                   # Use auto config: Yes
      sleep 2
      echo "n"                   # Shared Drive: No
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
      notify-send "Google Drive" "Mounted successfully at $MOUNT_POINT" -i folder-remote
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
get_credentials
configure_rclone
mount_drive
zeninf "$msg018"