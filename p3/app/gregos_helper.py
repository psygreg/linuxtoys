"""GregOS post-install trigger.

GregOS is a custom Bazzite-based image (``ghcr.io/psygreg/gregos``). Its
post-install script (``libs/gregos.bash``) should run once per configured
version, without the user having to invoke it manually.

The version lives in the script's ``# gregos-version:`` header. After a
successful run this module records that version in ``~/.config/linuxtoys/gregos``.
On every launch, if the booted image is GregOS and the recorded version differs
from the script header (missing, older, or the header was bumped), the script is
run again and the marker rewritten. When the marker already matches, nothing runs.

Version specification and marker bookkeeping both happen here, on the Python
side, so ``gregos.bash`` itself never needs to know whether it has already run.
"""

import logging
import os

from . import compat
from .lang_utils import get_config_dir

logger = logging.getLogger(__name__)

# Name of the post-install script (without extension) resolved through the
# normal manifest/script lookup so it executes with the canonical runner.
SCRIPT_NAME = "gregos"

# Marker file recording the last successfully applied GregOS setup version.
MARKER_FILENAME = "gregos"

# Header on gregos.bash whose value is the setup version to compare.
VERSION_HEADER = "gregos-version"

# Where gregos.bash lives relative to SCRIPT_DIR (it is a library script, not a
# catalog entry, so it is addressed by direct path rather than category lookup).
SCRIPT_RELPATH = os.path.join("libs", "gregos.bash")


def get_marker_path():
    """Return the path of the version marker file."""
    return os.path.join(get_config_dir(), MARKER_FILENAME)


def read_marker_version():
    """Return the last applied setup version, or None when absent/unreadable."""
    try:
        with open(get_marker_path(), "r", encoding="utf-8") as handle:
            value = handle.read().strip()
    except OSError:
        return None
    return value or None


def write_marker_version(version):
    """Record ``version`` as the last successfully applied setup version."""
    marker = get_marker_path()
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(f"{version}\n")
        return True
    except OSError as exc:
        logger.warning("Could not write GregOS setup marker: %s", exc)
        return False


def get_script_path():
    """Return the absolute path of gregos.bash, or None when unavailable."""
    script_dir = os.environ.get("SCRIPT_DIR")
    if not script_dir:
        return None
    path = os.path.join(script_dir, SCRIPT_RELPATH)
    return path if os.path.isfile(path) else None


def get_required_version(script_path=None):
    """Return the setup version declared by gregos.bash's header, or None."""
    if script_path is None:
        script_path = get_script_path()
    if not script_path:
        return None
    try:
        headers = compat.get_script_file_data(script_path)["headers"]
    except Exception:
        return None
    value = str(headers.get(VERSION_HEADER) or "").strip()
    return value or None


def setup_needed():
    """Return (needed, required_version, applied_version).

    ``needed`` is True when the booted image is GregOS and the marker does not
    already record the script's current ``# gregos-version:``. On non-GregOS
    hosts, or when the version is undeclared, nothing is ever needed.
    """
    if not compat.is_gregos():
        return False, None, None

    required = get_required_version()
    if not required:
        return False, None, None

    applied = read_marker_version()
    needed = applied != required
    return needed, required, applied


def _run_setup_script(script_path):
    """Run gregos.bash headlessly and return its exit code."""
    from . import library_loader
    from . import manifest_helper

    script_info = library_loader.script_info_from_path(
        script_path, os.environ.get("SCRIPT_DIR", "")
    )
    # This runs unattended; keep it out of the transaction registry so the
    # automatic pass is not mistaken for a user-installable feature.
    script_info["registry_name"] = SCRIPT_NAME
    return manifest_helper.run_script(script_info)


def run_setup_if_needed():
    """Run the GregOS post-install script when the marker is stale.

    Returns True when a run was attempted and completed successfully (and the
    marker was updated), False when nothing needed to run or the run failed.
    """
    needed, required, applied = setup_needed()
    if not needed:
        return False

    script_path = get_script_path()
    if not script_path:
        logger.warning("GregOS setup needed but %s was not found", SCRIPT_RELPATH)
        return False

    logger.info(
        "Running GregOS post-install setup (applied=%s, required=%s)",
        applied,
        required,
    )
    try:
        code = _run_setup_script(script_path)
    except Exception as exc:
        logger.warning("GregOS post-install setup failed: %s", exc)
        return False

    if code != 0:
        logger.warning("GregOS post-install setup exited with code %s", code)
        return False

    write_marker_version(required)
    return True
