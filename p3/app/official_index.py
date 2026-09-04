import os

# Script filenames without the .sh extension.
#
# Only scripts maintained with first-party support by LinuxToys
# should be included here.
VERIFIED_SCRIPTS = {
    "rstudio",
    "slothbash"
}


def is_verified_script(script_path):
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

    return is_verified_name(script_name)

def is_verified_name(name):
    """Return True if a software entry has first-party LinuxToys support."""
    if not name:
        return False

    normalized = str(name).strip().lower()
    return normalized in {item.lower() for item in VERIFIED_SCRIPTS}

def get_verified_names():
    """Return first-party-supported software names in display-friendly order."""
    return sorted(VERIFIED_SCRIPTS, key=str.casefold)

def get_verified_entries(translations=None):
    """
    Return (internal_name, display_name) pairs for officially supported apps.
    """
    from . import parser

    entries = [
        (
            name,
            parser.get_display_name(name, translations),
        )
        for name in VERIFIED_SCRIPTS
    ]

    return sorted(
        entries,
        key=lambda item: item[1].casefold(),
    )