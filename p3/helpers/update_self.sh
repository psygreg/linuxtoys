#!/bin/bash

# ---
# Lintoy-PoC Updater Script
# This script checks for remote git updates and asks the user if they want to apply them.
# TODO STRICTER VERSIONING - CHECK RELEASES ONLY AND SEND USER TO PAGE
# ---

# First, check if git and zenity are installed. If not, we can't proceed.
if ! command -v git &> /dev/null || ! command -v zenity &> /dev/null; then
    echo "Update check skipped: 'git' or 'zenity' command not found."
    exit 0
fi

echo "Checking for updates..."

# 1. Silently fetch the latest changes from the remote repository.
# We redirect output to /dev/null to hide it from the terminal.
# The '|| exit 0' part ensures that if this fails (e.g., no internet),
# the script just exits gracefully without showing an error to the user.
git fetch &> /dev/null || exit 0

# 2. Check the status to see if our local branch is behind the remote one.
# We use 'grep' to look for the specific phrase "Your branch is behind".
UPDATE_AVAILABLE=$(git status -uno | grep "Your branch is behind")

# 3. If the phrase is found, then an update is available.
if [[ ! -z "$UPDATE_AVAILABLE" ]]; then

    # 4. Ask the user if they want to update now using a Zenity question dialog.
    zenity --question --title="Update Available" --text="A new version of LinuxToys is available.\nWould you like to update now?" --width=300

    # 5. Check the user's response. '$?' holds the exit code of the last command.
    # Zenity question dialog returns 0 for "Yes" and 1 for "No".
    if [[ $? -eq 0 ]]; then
        
        # 6. If "Yes", show a pulsing progress bar while we run 'git pull'.
        # The '( ... )' creates a subshell, allowing us to pipe its output.
        (
            echo "# Pulling latest changes from the repository..."
            git pull
            sleep 2 # Add a small delay so the user can see the final message
            echo "# Update complete!"
        ) | zenity --progress --title="Updating..." --pulsate --auto-close --no-cancel --width=400

        # 7. Show a final confirmation dialog.
        zenity --info --title="Update Complete" --text="LinuxToys has been updated.\nThe application will now restart." --width=300

        # 8. Restart the application.
        # 'exec' replaces the current script process with the new one.
        echo "Restarting application..."
        exec python3 run.py
        
    else
        # If "No", just print a message and continue.
        echo "Update skipped by user."
        exit 0
    fi
else
    # If no update is available, just print a status and exit.
    echo "Application is up to date."
    exit 0
fi
