"""
Registry-based revert helper for undoing LinuxToys script installations.

Uses the execution registry to track and reverse operations performed during script execution.
Each operation is reversed, with file restorations from .bak files and package removals executed.
"""

import os
import tempfile
import subprocess


def _run_ok(cmd):
    """Execute a command and return True if successful."""
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    except Exception:
        return False


def _detect_package_manager():
    """Detect which package manager is available on the system."""
    if _run_ok(["bash", "-lc", "command -v rpm-ostree >/dev/null 2>&1"]):
        return "rpm-ostree"
    if _run_ok(["bash", "-lc", "command -v apt >/dev/null 2>&1"]):
        return "apt"
    if _run_ok(["bash", "-lc", "command -v dnf >/dev/null 2>&1"]):
        return "dnf"
    if _run_ok(["bash", "-lc", "command -v pacman >/dev/null 2>&1"]):
        return "pacman"
    if _run_ok(["bash", "-lc", "command -v zypper >/dev/null 2>&1"]):
        return "zypper"
    if _run_ok(["bash", "-lc", "command -v eopkg >/dev/null 2>&1"]):
        return "eopkg"
    return None


def _load_from_transmap(transmap_path):
    """
    Load operations from a transmap file created during script execution.
    
    Returns a list of operation strings in the order they appear in the file.
    Returns empty list if file doesn't exist or cannot be read.
    """
    if not os.path.exists(transmap_path):
        return []
    
    try:
        with open(transmap_path, "r") as f:
            content = f.read()
    except Exception:
        return []
    
    operations = []
    
    # Parse operation lines (format: "operation_type operand1 operand2 ...")
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):  # Skip empty lines and comments
            operations.append(line)
    
    return operations


def _load_last_execution(script_name):
    """
    Load the last execution record from the registry for the given script.
    
    Returns a list of operations (operation_type, operands) or empty list if not found.
    Operations are in the order they appear in registry (original execution order).
    """
    registry_file = os.path.expanduser("~/.cache/linuxtoys/registry")
    
    if not os.path.exists(registry_file):
        return []
    
    try:
        with open(registry_file, "r") as f:
            content = f.read()
    except Exception:
        return []
    
    # Split by registry entries (format: [timestamp] Script: name\nChanges:\n  - operation)
    entries = content.split("---\n")
    entries.reverse()  # Start from most recent
    
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        
        lines = entry.split("\n")
        if not lines:
            continue
        
        # First line should have the script name
        first_line = lines[0] if lines else ""
        if f"Script: {script_name}" not in first_line:
            continue
        
        # Found the matching script execution
        operations = []
        
        # Parse operation lines (those starting with "  - ")
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- "):
                # Remove "- " prefix and parse operation
                op_line = line[2:].strip()
                if op_line and op_line != "Changes:" and op_line != "Changes: (none)":
                    operations.append(op_line)
        
        return operations
    
    return []


def _parse_operation(op_line):
    """
    Parse an operation line from the transmap.
    
    Returns a tuple of (operation_type, operands_list)
    E.g., "pkg curl git vim" -> ("pkg install", ["curl", "git", "vim"])
          "pkg rm curl" -> ("pkg rm", ["curl"])
          "pkg file /path/to/pkg.deb" -> ("pkg file", ["/path/to/pkg.deb"])
          "edited /etc/config" -> ("edited", ["/etc/config"])
          "sysd enabled ssh" -> ("sysd", ["enabled", "ssh"])
          "flatpak app1 app2" -> ("flatpak", ["app1", "app2"])
          "chsh /bin/zsh" -> ("chsh", ["/bin/zsh"])
    """
    parts = op_line.split()
    if not parts:
        return None, []
    
    op_type = parts[0]
    
    if len(parts) > 1:
        # For operations with multiple parts (e.g., "sysd enabled service")
        if op_type == "sysd":
            # sysd operations have format: "sysd action service"
            if len(parts) >= 3:
                return op_type, [parts[1], parts[2]]  # ["enabled", "ssh"]
            else:
                return op_type, parts[1:] if len(parts) > 1 else []
        elif op_type == "pkg":
            # pkg operations have different formats:
            # "pkg rm package" -> distinguish removal
            # "pkg file /path" -> distinguish from file
            # "pkg package1 package2" -> regular installation
            if len(parts) >= 2 and parts[1] == "rm":
                # Removal: "pkg rm curl" or "pkg rm curl git"
                return "pkg rm", parts[2:]
            elif len(parts) >= 2 and parts[1] == "file":
                # From file: "pkg file /path/to/file"
                return "pkg file", parts[2:]
            else:
                # Installation: "pkg curl git vim"
                return "pkg install", parts[1:]
        elif op_type == "flatpak":
            # flatpak can have multiple operands (e.g., "flatpak app1 app2")
            return op_type, parts[1:]
        elif op_type == "chsh":
            # Shell change: "chsh /bin/zsh"
            return op_type, parts[1:]
        else:
            # Most operations: "type operand" (e.g., "edited /etc/config")
            return op_type, [parts[1]]
    
    return op_type, []


def _reverse_package_install(packages, package_manager):
    """Reverse a package installation by removing it(s).
    
    Args:
        packages: list of package names or single package name string
        package_manager: detected package manager
    
    Returns:
        list of shell commands to reverse the package installation
    """
    if not package_manager:
        return []
    
    # Normalize to list
    if isinstance(packages, str):
        packages = [packages]
    
    if not packages:
        return []
    
    # Use pkg_remove library function to handle distro-specific removal
    pkg_args = " ".join(packages)
    return [f"pkg_remove {pkg_args}"]


def _reverse_package_removal(packages, package_manager):
    """Reverse a package removal by reinstalling it(s).
    
    Args:
        packages: list of package names or single package name string
        package_manager: detected package manager
    
    Returns:
        list of shell commands to reverse the package removal
    """
    if not package_manager:
        return []
    
    # Normalize to list
    if isinstance(packages, str):
        packages = [packages]
    
    if not packages:
        return []
    
    # Use pkg_install library function to handle distro-specific reinstallation
    pkg_args = " ".join(packages)
    return [f"pkg_install {pkg_args}"]


def _reverse_package_fromfile(file_paths):
    """Reverse a package-from-file installation by removing it(s).
    
    Attempts to extract package name from file path and remove it.
    For .deb files, extracts name before first underscore.
    For .pkg.tar.zst files, similar approach.
    For .flatpak bundles, extracts app ID using flatpak info.
    
    Args:
        file_paths: list of file paths or single file path string
    
    Returns:
        list of shell commands to reverse the package installation
    """
    # Normalize to list
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    if not file_paths:
        return []
    
    packages_to_remove = []
    flatpak_app_ids = []
    
    for file_path in file_paths:
        basename = os.path.basename(file_path)
        
        # Handle flatpak bundles specially
        if basename.endswith('.flatpak'):
            # Try to extract app ID from the flatpak bundle using flatpak info
            try:
                result = subprocess.run(
                    ["flatpak", "info", file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    # Parse output to find ID= line
                    for line in result.stdout.split('\n'):
                        if line.startswith('ID='):
                            app_id = line.split('=', 1)[1].strip()
                            flatpak_app_ids.append(app_id)
                            break
            except Exception:
                pass
            continue
        
        # Extract package name from filename for other package types
        if basename.endswith('.deb'):
            # For deb files: package_1.0-1_amd64.deb -> package
            pkg_name = basename.split('_')[0]
            packages_to_remove.append(pkg_name)
        elif basename.endswith('.pkg.tar.zst') or basename.endswith('.pkg.tar.xz'):
            # For arch packages: package-1.0-1-x86_64.pkg.tar.zst -> package
            pkg_name = basename.split('-')[0]
            packages_to_remove.append(pkg_name)
        elif basename.endswith('.rpm'):
            # For rpm files: package-1.0-1.fc35.x86_64.rpm -> package
            pkg_name = basename.replace('.rpm', '').rsplit('-', 2)[0]
            packages_to_remove.append(pkg_name)
    
    # Build reversal commands
    reversal_commands = []
    
    if packages_to_remove:
        # Use pkg_remove library function to safely remove the packages
        pkg_args = " ".join(packages_to_remove)
        reversal_commands.append(f"pkg_remove {pkg_args}")
    
    if flatpak_app_ids:
        # Use flatpak uninstall for extracted app IDs
        for app_id in flatpak_app_ids:
            cmd = (
                f"flatpak uninstall --user --noninteractive {app_id} 2>/dev/null || true ; "
                f"sudo flatpak uninstall --system --noninteractive {app_id} 2>/dev/null || true"
            )
            reversal_commands.append(cmd)
    
    return reversal_commands


def _reverse_file_restoration(file_path):
    """Reverse a file or directory change by restoring from .bak file/directory."""
    backup_path = f"{file_path}.bak"
    
    # Check if backup exists
    if not os.path.exists(backup_path):
        return None
    
    # Use rm -rf to handle both files and directories, moving backup back into place
    return f"{{ rm -rf {file_path} && mv {backup_path} {file_path}; }} || true"


def _reverse_flatpak_removal(app_ids):
    """Reverse flatpak installation(s) by removing it/them.
    
    Args:
        app_ids: list of app IDs or single app ID string
    
    Returns:
        list of shell commands to reverse the flatpak installation
    """
    # Normalize to list
    if isinstance(app_ids, str):
        app_ids = [app_ids]
    
    if not app_ids:
        return []
    
    commands = []
    for app_id in app_ids:
        # Remove from both user and system scopes
        cmd = (
            f"flatpak uninstall --user --noninteractive {app_id} 2>/dev/null || true ; "
            f"sudo flatpak uninstall --system --noninteractive {app_id} 2>/dev/null || true"
        )
        commands.append(cmd)
    
    return commands


def _reverse_systemd_operation(service, action):
    """Reverse systemd operations."""
    reversals = {
        "enabled": "sudo systemctl disable",
        "disabled": "sudo systemctl enable",
        "started": "sudo systemctl stop",
        "stopped": "sudo systemctl start",
    }
    
    if action not in reversals:
        return None
    
    return f"{reversals[action]} {service}"


def _reverse_bootloader_update():
    """
    Reverse a bootloader update by triggering another bootloader update.
    
    Bootloader updates are idempotent, so re-running the update ensures
    consistency and reverses any partial or corrupted state.
    Uses the bootloader_upd function from linuxtoys.lib for proper distro handling.
    """
    return "bootloader_upd"


def _reverse_initramfs_update():
    """
    Reverse an initramfs update by triggering another initramfs update.
    
    Initramfs updates are idempotent, so re-running the update ensures
    consistency and reverses any partial or corrupted state.
    Uses the initramfs_upd function from linuxtoys.lib for proper distro handling.
    """
    return "initramfs_upd"


def _reverse_shell_change(shell_path):
    """Reverse a shell change by reverting to bash.
    
    Args:
        shell_path: the shell that was changed to (ignored, always revert to bash)
    
    Returns:
        list containing a single shell_change command to revert to bash
    """
    # Always revert to /bin/bash, the standard default shell
    return ["shell_change /bin/bash $USER"]


def _reverse_kargs_update(karg):
    """
    Reverse a kernel argument update by deleting the appended karg.
    
    Uses rpm-ostree kargs --delete to remove the previously appended kernel argument.
    """
    if not karg:
        return None
    
    return f"sudo rpm-ostree kargs --delete=\"{karg}\" || true"


def _reverse_operation(op_line, package_manager):
    """
    Generate shell command(s) to reverse a single operation.
    
    Returns a list of command strings or empty list if unable to reverse.
    """
    op_type, operands = _parse_operation(op_line)
    
    if op_type == "pkg install" and operands:
        # Reverse package installation by removing
        return _reverse_package_install(operands, package_manager)
    
    elif op_type == "pkg rm" and operands:
        # Reverse package removal by reinstalling
        return _reverse_package_removal(operands, package_manager)
    
    elif op_type == "pkg file" and operands:
        # Reverse package-from-file installation by removing
        return _reverse_package_fromfile(operands)
    
    elif op_type == "flatpak" and operands:
        return _reverse_flatpak_removal(operands)
    
    elif op_type == "chsh" and operands:
        # Reverse shell change by reverting to bash
        return _reverse_shell_change(operands[0])
    
    elif op_type in ("edited", "created", "removed") and operands:
        # All file operations use the same restoration mechanism
        # File operations typically have one file per operation
        cmd = _reverse_file_restoration(operands[0])
        return [cmd] if cmd else []
    
    elif op_type == "sysd" and len(operands) >= 2:
        action, service = operands[0], operands[1]
        cmd = _reverse_systemd_operation(service, action)
        return [cmd] if cmd else []
    
    elif op_type == "updated" and "bootloader" in op_line:
        # Bootloader updates need to be re-run to ensure consistency
        cmd = _reverse_bootloader_update()
        return [cmd] if cmd else []
    
    elif op_type == "updated" and "initramfs" in op_line:
        # Initramfs updates need to be re-run to ensure consistency
        cmd = _reverse_initramfs_update()
        return [cmd] if cmd else []
    
    elif op_type == "updated" and "kargs" in op_line:
        # Extract the kargs value from "updated kargs kernel-argument"
        parts = op_line.split(None, 2)  # ["updated", "kargs", "kernel-argument"]
        if len(parts) >= 3:
            karg = parts[2]
            cmd = _reverse_kargs_update(karg)
            return [cmd] if cmd else []
        return []
    
    return []


def build_uninstall_script_entry(script_info, translations=None):
    """
    Build a temporary uninstall script for a given LinuxToys script.
    
    Reads the last execution record from the registry and generates
    reverse operations to undo the changes.
    
    Returns a script_info-like dict or None when no removable components were found.
    """
    script_path = script_info.get("path")
    if not script_path or not os.path.isfile(script_path):
        return None
    
    script_name = script_info.get("name", "unknown")
    
    # Load the last execution from registry
    operations = _load_last_execution(script_name)
    
    if not operations:
        # No registry entry found for this script
        return None
    
    package_manager = _detect_package_manager()
    
    # Generate reverse commands (in reverse order)
    reverse_commands = []
    for op_line in reversed(operations):
        cmds = _reverse_operation(op_line, package_manager)
        if cmds:
            reverse_commands.extend(cmds)
    
    if not reverse_commands:
        # No reversible operations found
        return None
    
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    lines = [
        "#!/bin/bash",
        "set -eo pipefail",
        f'SCRIPT_DIR="{script_dir}"',
        'source "$SCRIPT_DIR/libs/linuxtoys.lib"',
        'source "$SCRIPT_DIR/libs/helpers.lib"',
    ]
    
    # Check if we need sudo
    needs_sudo = any(
        cmd.strip().startswith("sudo ") for cmd in reverse_commands
    )
    
    if needs_sudo:
        lines.append("")
        lines.append("# Request sudo authorization")
        lines.append("sudo_rq")
    
    lines.append("")
    lines.append("# Reverse operations (in reverse order, most recent first)")
    lines.extend(reverse_commands)
    lines.append("")
    lines.append('echo "Removal completed."')
    
    # Write temporary script
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="linuxtoys-uninstall-", suffix=".sh", delete=False
        ) as temp_script:
            temp_script.write("\n".join(lines) + "\n")
            temp_path = temp_script.name
    except Exception:
        return None
    
    os.chmod(temp_path, 0o700)
    
    # Prepare return entry
    script_name_display = script_info.get("name", "Script")
    remove_name = (
        translations.get("remove_action_name", "Remove {name}")
        if translations
        else "Remove {name}"
    ).format(name=script_name_display)
    
    return {
        "icon": script_info.get("icon", "application-x-executable"),
        "name": remove_name,
        "description": translations.get(
            "remove_action_desc",
            "Automatically removes components installed by this script using the registry.",
        )
        if translations
        else "Automatically removes components installed by this script using the registry.",
        "repo": script_info.get("repo", ""),
        "path": temp_path,
        "is_script": True,
        "cleanup_path": temp_path,
    }


def build_auto_revert_script_entry(script_info, transmap_path, translations=None):
    """
    Build a temporary auto-revert script for a script that exited with an error.
    
    Reads the transmap file created during script execution and generates
    reverse operations to undo the changes made before the error occurred.
    
    Returns a script_info-like dict or None when no reversible operations were found.
    """
    if not os.path.exists(transmap_path):
        return None
    
    # Load operations from the transmap file
    operations = _load_from_transmap(transmap_path)
    
    if not operations:
        # No operations found in transmap
        return None
    
    package_manager = _detect_package_manager()
    
    # Generate reverse commands (in reverse order - undo most recent first)
    reverse_commands = []
    for op_line in reversed(operations):
        cmds = _reverse_operation(op_line, package_manager)
        if cmds:
            reverse_commands.extend(cmds)
    
    if not reverse_commands:
        # No reversible operations found
        return None
    
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    lines = [
        "#!/bin/bash",
        "set -eo pipefail",
        f'SCRIPT_DIR="{script_dir}"',
        'source "$SCRIPT_DIR/libs/linuxtoys.lib"',
        'source "$SCRIPT_DIR/libs/helpers.lib"',
    ]
    
    # Check if we need sudo
    needs_sudo = any(
        cmd.strip().startswith("sudo ") for cmd in reverse_commands
    )
    
    if needs_sudo:
        lines.append("")
        lines.append("# Request sudo authorization")
        lines.append("sudo_rq")
    
    lines.append("")
    lines.append("# Reverse operations from failed script execution (in reverse order)")
    lines.extend(reverse_commands)
    lines.append("")
    lines.append('echo "Automatic reversion completed."')
    
    # Write temporary script
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="linuxtoys-auto-revert-", suffix=".sh", delete=False
        ) as temp_script:
            temp_script.write("\n".join(lines) + "\n")
            temp_path = temp_script.name
    except Exception:
        return None
    
    os.chmod(temp_path, 0o700)
    
    # Prepare return entry
    script_name_display = script_info.get("name", "Script")
    revert_name = (
        translations.get("auto_revert_action_name", "Auto-revert {name}")
        if translations
        else "Auto-revert {name}"
    ).format(name=script_name_display)
    
    return {
        "icon": script_info.get("icon", "application-x-executable"),
        "name": revert_name,
        "description": translations.get(
            "auto_revert_action_desc",
            "Automatically reverts components installed by this script before it failed.",
        )
        if translations
        else "Automatically reverts components installed by this script before it failed.",
        "repo": script_info.get("repo", ""),
        "path": temp_path,
        "is_script": True,
        "cleanup_path": temp_path,
    }
