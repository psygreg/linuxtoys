# LinuxToys Update System

## Overview

LinuxToys now has a robust dual update system that works for both development and packaged versions:

1. **Git-based updates** (for development/git-cloned versions in CLI mode)
2. **GitHub API-based updates** (for all versions, including packaged releases)

## How it Works

### CLI Mode
- When running with `LT_MANIFEST=1`, the application operates in CLI mode
- In CLI mode, git-based updates are used (via `helpers/update_self.sh`)
- CLI mode also supports checking for updates with: `LT_MANIFEST=1 python run.py check-updates`

### GUI Mode
- In GUI mode, the new GitHub API-based update checker is used
- This works for both git-cloned and packaged versions
- Checks the latest release tag on GitHub and compares with the current version
- Shows a native GTK dialog asking if the user wants to download the update
- Dialog supports translations (English and Portuguese currently)
- If user clicks "Download Update", opens the GitHub releases page in the default browser

## Files

### `app/update_helper.py`
- Main update checker using GitHub API
- Reads current version from `../src/ver` file (with hardcoded fallback)
- Functions:
  - `get_current_version()`: Read version from file or fallback
  - `check_for_updates()`: Check if update is available
  - `get_latest_github_release()`: Fetch latest release from GitHub
  - `compare_versions()`: Compare version strings
  - `show_update_dialog()`: Shows GTK dialog with translation support
  - `run_update_check()`: Main function with dialog support

### `helpers/update_self.sh`
- Git-based updater for development versions
- Only used in CLI mode now
- Uses `git fetch` and `git pull` to update
- Shows zenity dialogs for user interaction

### Modified Files
- `run.py`: Only runs git updater in CLI mode
- `app/main.py`: Uses new update checker in GUI mode, conditional imports for CLI compatibility
- `app/cli_helper.py`: Added CLI update check command

## Usage

### For Users
- **GUI Mode**: Updates are automatically checked on startup
- **CLI Mode**: Use `LT_MANIFEST=1 python run.py check-updates`

### For Developers

#### Updating the Version Number
Use the provided helper script:
```bash
python update_version.py 4.4
```

This will update both:
1. The main version file `../src/ver`
2. The fallback version in `app/update_helper.py` (if needed)

Or manually edit `../src/ver` and change the version number there.

#### Creating a Release
1. Update the version number using `update_version.py`
2. Commit the change
3. Create a new release tag on GitHub
4. The update system will automatically detect the new version

## Testing

### Test Current Version Check
```bash
cd p3
python -c "from app.update_helper import run_update_check; run_update_check(show_dialog=False, verbose=True)"
```

### Test CLI Update Check
```bash
cd p3
LT_MANIFEST=1 python run.py check-updates
```

### Test Update Detection (with fake lower version)
```bash
cd p3
python -c "
from app.update_helper import run_update_check, CURRENT_VERSION
from app.lang_utils import load_translations
import app.update_helper as uh
original = uh.CURRENT_VERSION
uh.CURRENT_VERSION = '4.0'  # Fake lower version
result = run_update_check(show_dialog=False, verbose=True, translations=load_translations())
uh.CURRENT_VERSION = original
print(f'Update detected: {result}')
"
```

### Test GUI Update Dialog (with fake lower version)
```bash
cd p3
python -c "
from app.update_helper import _show_gtk_update_dialog
from app.lang_utils import load_translations
# This will show the actual dialog - close it to continue
result = _show_gtk_update_dialog('4.4', load_translations())
print(f'User chose to update: {result}')
"
```

## Dependencies

The update system requires:
- Python 3.x with `urllib` and `json` (built-in)
- `PyGObject` and `Gtk+ 3.0` for GUI dialogs
- `xdg-open` for opening browser (optional)

No additional Python packages are required for the core update functionality.

## Translation Support

The update dialog supports translations stored in `libs/lang/`:
- English (`en.json`)
- Portuguese (`pt.json`)

Translation keys used:
- `update_available_title`: Dialog title
- `update_available_message`: Main message
- `update_current_version`: Current version label
- `update_latest_version`: Latest version label  
- `update_download_btn`: Download button text
- `update_ignore_btn`: Ignore button text
