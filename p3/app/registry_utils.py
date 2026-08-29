import os
import re


def parse_registry_file():
    registry_file = os.path.expanduser("~/.cache/linuxtoys/registry")

    if not os.path.exists(registry_file):
        return {}

    try:
        with open(registry_file, "r") as f:
            content = f.read()
    except Exception:
        return {}

    entry_pattern = (
        r'\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\]]*\] '
        r'Script: ([^\n]+)'
    )

    scripts_registry = {}
    matches = list(re.finditer(entry_pattern, content))

    for i, match in enumerate(matches):
        script_name = match.group(1).strip()
        if not script_name:
            continue

        entry_start = match.start()
        entry_end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(content)
        )
        entry_text = content[entry_start:entry_end]

        timestamp_match = re.search(r'\[([^\]]+)\]', entry_text)
        timestamp = timestamp_match.group(1) if timestamp_match else ""

        operations = []
        in_changes = False

        for line in entry_text.split("\n"):
            line_stripped = line.strip()

            if line_stripped.startswith("Changes:"):
                in_changes = True
                continue

            if in_changes and line_stripped.startswith("- "):
                op_line = line_stripped[2:].strip()

                if op_line and op_line != "(none)":
                    operations.append(op_line)

        scripts_registry.setdefault(script_name, []).append(
            (timestamp, operations)
        )

    return scripts_registry

def search_registry_entries(registry_data, query):
    """
    Search registry entries by script name, timestamp, or operation text.

    Args:
        registry_data:
            Dict in the form:
            {
                script_name: [
                    (timestamp, [operations]),
                    ...
                ]
            }

        query:
            Search string.

    Returns:
        A filtered registry dict using the same structure as registry_data.

        If the script name matches, all executions for that script are
        returned. Otherwise, only executions containing a matching timestamp
        or operation are returned.
    """
    query = query.strip().casefold()

    if not query:
        return dict(registry_data)

    results = {}

    for script_name, executions in registry_data.items():
        # A script-name match includes all executions.
        if query in script_name.casefold():
            results[script_name] = executions
            continue

        matching_executions = []

        for timestamp, operations in executions:
            timestamp_text = str(timestamp or "")

            timestamp_matches = query in timestamp_text.casefold()
            operation_matches = any(
                query in str(operation).casefold()
                for operation in operations
            )

            if timestamp_matches or operation_matches:
                matching_executions.append((timestamp, operations))

        if matching_executions:
            results[script_name] = matching_executions

    return results