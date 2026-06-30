"""
File watcher for LinuxToys developer mode.

Monitors scripts and libraries directories for changes and triggers
UI reload automatically. Only active when DEV_MODE=1.

Uses polling via GLib.timeout_add_seconds (no external dependencies).
"""

import os

from . import dev_mode, parser


def _get_dir_mtimes(directory):
    """Get modification times for all files in a directory tree."""
    mtimes = {}
    if not os.path.isdir(directory):
        return mtimes
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                mtimes[fpath] = os.stat(fpath).st_mtime
            except OSError:
                pass
    return mtimes


def _detect_changes(old_mtimes, new_mtimes):
    """Return list of changed file paths by comparing two mtime dicts."""
    changed = []
    all_paths = set(old_mtimes) | set(new_mtimes)
    for fpath in all_paths:
        if old_mtimes.get(fpath) != new_mtimes.get(fpath):
            changed.append(fpath)
    return changed


def start(window):
    """Start the file watcher if DEV_MODE is enabled.

    Polls every 2 seconds for file changes in SCRIPTS_DIR and libs/.
    Calls window._on_files_changed(changed_files) via GLib.idle_add
    when changes are detected.

    Args:
        window: AppWindow instance to notify on changes.
    """
    if not dev_mode.is_dev_mode_enabled():
        return

    app_dir = os.path.dirname(os.path.abspath(parser.__file__))
    parent_dir = os.path.dirname(app_dir)

    scripts_dir = parser.SCRIPTS_DIR
    libs_dir = os.path.join(parent_dir, 'libs')

    watched_dirs = [d for d in [scripts_dir, libs_dir, app_dir] if os.path.isdir(d)]

    prev_mtimes = {}
    reload_pending = [False]

    for d in watched_dirs:
        prev_mtimes[d] = _get_dir_mtimes(d)

    def _poll():
        any_change = False
        all_changed = []
        for d in watched_dirs:
            curr = _get_dir_mtimes(d)
            changed = _detect_changes(prev_mtimes[d], curr)
            if changed:
                any_change = True
                all_changed.extend(changed)
            prev_mtimes[d] = curr

        if any_change and not reload_pending[0]:
            reload_pending[0] = True

            def _notify():
                reload_pending[0] = False
                try:
                    window._on_files_changed(all_changed)
                except Exception as e:
                    print(f"File watcher error: {e}")
                return False

            from .gtk_common import GLib
            GLib.idle_add(_notify)

        return True

    from .gtk_common import GLib
    GLib.timeout_add_seconds(2, _poll)
