import re
import shutil
import os

from .revert_helper import build_auto_revert_script_entry
from .action_registry import parse_registry_file

class ExecutionRegistry:
    @staticmethod
    def _cleanup_tmp_noram_dirs(transmap_path):
        """
        Clean up temporary directories created by prep_tmp_noram.
        Reads transmap file for tmpdir_noram entries and removes those directories.
        """
        if not os.path.exists(transmap_path):
            return
    
        try:
            with open(transmap_path, 'r') as f:
                content = f.read()
        
            # Find all tmpdir_noram entries
            pattern = r'tmpdir_noram\s+(\S+)'
            matches = re.findall(pattern, content)
        
            for tmpdir_path in matches:
                if os.path.exists(tmpdir_path):
                    try:
                        shutil.rmtree(tmpdir_path)
                    except Exception:
                        pass  # Silently ignore cleanup errors
        except Exception:
            pass  # Silently ignore transmap read errors

    @staticmethod
    def _remove_old_script_entries_from_registry(script_name):
        """
        Remove all existing entries for a script from the registry file.
        This ensures each script only has the most recent run in the registry.
        
        Returns True if entries were removed or file doesn't exist, False on error.
        """
        
        registry_file = os.path.expanduser("~/.cache/linuxtoys/registry")
        
        if not os.path.exists(registry_file):
            return True
        
        try:
            with open(registry_file, "r") as f:
                content = f.read()
        except Exception:
            return False
        
        # Use regex to find all entries and filter by script name
        entry_pattern = r'\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*\] Script: ([^\n]+)'
        matches = list(re.finditer(entry_pattern, content))
        
        if not matches:
            return True  # No entries found, nothing to filter
        
        # Build list of ranges to keep (entries NOT matching this script)
        ranges_to_keep = []
        for i, match in enumerate(matches):
            script_name_in_entry = match.group(1).strip()
            if script_name_in_entry == script_name:
                # Skip this entry
                continue
            
            entry_start = match.start()
            entry_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            ranges_to_keep.append((entry_start, entry_end))
        
        # Reconstruct file from kept ranges
        try:
            if not ranges_to_keep:
                # All entries were for this script, clear the file
                new_content = ""
            else:
                new_content = "".join(content[start:end] for start, end in ranges_to_keep)
            
            with open(registry_file, "w") as f:
                f.write(new_content)
            return True
        except Exception:
            return False
 
    @staticmethod
    def _save_to_registry(script_name, transmap_path):
        """Save script execution record to registry."""
        try:
            import datetime
            registry_dir = os.path.expanduser("~/.cache/linuxtoys")
            registry_file = os.path.join(registry_dir, "registry")
            
            # Create directory if it doesn't exist
            os.makedirs(registry_dir, exist_ok=True)
            
            # Remove old entries for this script to keep only the latest run
            ExecutionRegistry._remove_old_script_entries_from_registry(script_name)
            
            # Read transmap contents
            transmap_contents = ""
            if os.path.exists(transmap_path):
                try:
                    with open(transmap_path, "r") as f:
                        transmap_contents = f.read().strip()
                except (IOError, OSError):
                    pass
            
            # Format entry with timestamp
            timestamp = datetime.datetime.now().isoformat()
            entry = f"[{timestamp}] Script: {script_name}\n"
            if transmap_contents:
                entry += "Changes:\n"
                for line in transmap_contents.split("\n"):
                    if line.strip():
                        entry += f"  - {line}\n"
            else:
                entry += "Changes: (none)\n"
            entry += "---\n\n"
            
            # Append to registry file
            with open(registry_file, "a") as f:
                f.write(entry)
        except Exception:
            pass  # Silently ignore registry errors

    @staticmethod
    def _get_last_registry_execution(script_name) -> str:
        if not script_name:
            return ""

        try:
            registry_data = parse_registry_file()

            executions = registry_data.get(script_name, [])
            if not executions:
                return ""

            timestamp, operations = executions[-1]

            lines = [f"Last execution of '{script_name}':"]

            if timestamp:
                lines.append(f"Timestamp: {timestamp}")

            if operations:
                lines.append("")
                lines.append("Operations performed:")

                for operation in operations:
                    lines.append(f"  • {operation}")
            else:
                lines.extend([
                    "",
                    "Operations: (none)",
                ])

            return "\n".join(lines)
        except Exception:
            return ""
 
    @staticmethod
    def _try_auto_revert(transmap_path, script_name, translations):
        """
        Attempt to build an auto-revert script from transmap operations.
        
        Returns a script_info-like dict if revertible operations exist, None otherwise.
        """
        if not os.path.exists(transmap_path):
            return None

        if not script_name:
            return None

        current_script = {
            "name": script_name,
            "icon": "application-x-executable",
            "repo": "",
        }

        try:
            return build_auto_revert_script_entry(
                current_script,
                transmap_path,
                translations,
            )
        except Exception:
            return None