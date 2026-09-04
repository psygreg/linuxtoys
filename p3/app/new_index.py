import os


# Feature names without the .sh extension.
#
# Include features here while they should display the "New" marker.
# Supports both normal LinuxToys scripts and repository-list entries.
NEW_FEATURES = {
    # "example",
}


def is_new_script(script_path):
    """Return True if a physical script is currently marked as new."""
    if not script_path:
        return False

    normalized_path = os.path.normpath(script_path)
    local_scripts_dir = os.path.normpath(
        os.path.expanduser("~/.local/linuxtoys/scripts")
    )

    try:
        if os.path.commonpath(
            (normalized_path, local_scripts_dir)
        ) == local_scripts_dir:
            return False
    except ValueError:
        pass

    script_name = os.path.splitext(
        os.path.basename(normalized_path)
    )[0]

    return is_new_name(script_name)


def is_new_name(name):
    """Return True if a feature is currently marked as new."""
    if not name:
        return False

    normalized = str(name).strip().casefold()
    return normalized in {
        item.casefold()
        for item in NEW_FEATURES
    }