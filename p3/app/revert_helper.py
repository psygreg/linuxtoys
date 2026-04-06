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
    E.g., "pkg curl" -> ("pkg", ["curl"])
          "edited /etc/config" -> ("edited", ["/etc/config"])
          "sysd enabled ssh" -> ("sysd", ["enabled", "ssh"])
    """
    parts = op_line.split(None, 1)
    if not parts:
        return None, []
    
    op_type = parts[0]
    
    if len(parts) > 1:
        # For operations with multiple parts (e.g., "sysd enabled service")
        if op_type == "sysd":
            # sysd operations have format: "sysd action service"
            rest_parts = parts[1].split(None, 1)
            if len(rest_parts) == 2:
                return op_type, list(rest_parts)  # ["enabled", "ssh"]
            else:
                return op_type, rest_parts if rest_parts else []
        else:
            # Most operations: "type operand"
            return op_type, [parts[1]]
    
    return op_type, []


def _reverse_package_removal(package, package_manager):
    """Reverse a package installation by removing it."""
    if not package_manager or not package:
        return None
    
    manager_remove_map = {
        "apt": "sudo apt autoremove -y --allow-unauthenticated",
        "dnf": "sudo dnf remove -y",
        "pacman": "sudo pacman -Rns --noconfirm",
        "zypper": "sudo zypper rm -y",
        "rpm-ostree": "sudo rpm-ostree uninstall",
        "eopkg": "sudo eopkg rmf -y",
    }
    
    if package_manager not in manager_remove_map:
        return None
    
    cmd = manager_remove_map[package_manager]
    return f"{cmd} {package}"


def _reverse_file_restoration(file_path):
    """Reverse a file change by restoring from .bak file."""
    backup_path = f"{file_path}.bak"
    
    # Check if backup exists
    if not os.path.exists(backup_path):
        return None
    
    # Restore from backup
    return f"{{ rm -f {file_path} && mv {backup_path} {file_path}; }} || true"


def _reverse_flatpak_removal(app_id):
    """Reverse a flatpak installation by removing it."""
    # Remove from both user and system scopes
    return (
        f"flatpak uninstall --user --noninteractive {app_id} 2>/dev/null || true ; "
        f"sudo flatpak uninstall --system --noninteractive {app_id} 2>/dev/null || true"
    )


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
    Generate a shell command to reverse a single operation.
    
    Returns the command string or None if unable to reverse.
    """
    op_type, operands = _parse_operation(op_line)
    
    if op_type == "pkg" and operands:
        return _reverse_package_removal(operands[0], package_manager)
    
    elif op_type == "flatpak" and operands:
        return _reverse_flatpak_removal(operands[0])
    
    elif op_type in ("edited", "created", "removed") and operands:
        # All file operations use the same restoration mechanism
        return _reverse_file_restoration(operands[0])
    
    elif op_type == "sysd" and len(operands) >= 2:
        action, service = operands[0], operands[1]
        return _reverse_systemd_operation(service, action)
    
    elif op_type == "updated" and "bootloader" in op_line:
        # Bootloader updates need to be re-run to ensure consistency
        return _reverse_bootloader_update()
    
    elif op_type == "updated" and "initramfs" in op_line:
        # Initramfs updates need to be re-run to ensure consistency
        return _reverse_initramfs_update()
    
    elif op_type == "updated" and "kargs" in op_line:
        # Extract the kargs value from "updated kargs kernel-argument"
        parts = op_line.split(None, 2)  # ["updated", "kargs", "kernel-argument"]
        if len(parts) >= 3:
            karg = parts[2]
            return _reverse_kargs_update(karg)
        return None
    
    return None


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
        cmd = _reverse_operation(op_line, package_manager)
        if cmd:
            reverse_commands.append(cmd)
    
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
        cmd = _reverse_operation(op_line, package_manager)
        if cmd:
            reverse_commands.append(cmd)
    
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
