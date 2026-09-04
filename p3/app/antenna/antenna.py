import sys
import time
import traceback
import requests
from requests.exceptions import ConnectionError, Timeout
import json
from io import StringIO
from pathlib import Path
import base64
import hashlib
import hmac
import unicodedata
from ..updater import __version__
from urllib.parse import urlparse
 
_REPORT_URL = "https://bug.linux.toys"
 
# Cache directory for storing the generated secret (in user's config dir)
_CACHE_DIR = Path.home() / ".cache" / "linuxtoys" / "antenna"
_SECRET_CACHE = _CACHE_DIR / "bootstrap.json"
_HISTORY_FILE = _CACHE_DIR / "history.json"
 
# --- System Info Helpers ---
def _get_os_info() -> dict:
    """Extract OS identifier and version from /etc/os-release."""
    os_info = {"id": "unknown", "version": ""}
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    os_info["id"] = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("VERSION="):
                    os_info["version"] = line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return os_info

def _get_cpu_model() -> str:
    """Return the host CPU model name."""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()

                # Useful fallback for some ARM systems.
                if line.startswith("Processor"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass

    return "unknown"

def _get_gpu_info() -> dict:
    """Detect PCI display devices and return their human-readable names."""
    import subprocess

    devices = []
    has_nvidia = False

    for device in Path("/sys/bus/pci/devices").glob("*"):
        try:
            device_class = int(
                (device / "class").read_text(encoding="utf-8").strip(),
                16,
            )
        except (OSError, ValueError):
            continue

        # VGA, 3D and other display controllers.
        if device_class >> 16 != 0x03:
            continue

        try:
            vendor = int(
                (device / "vendor").read_text(encoding="utf-8").strip(),
                16,
            )
        except (OSError, ValueError):
            vendor = None

        if vendor == 0x10DE:
            has_nvidia = True

        gpu_name = ""

        # Prefer lspci because it resolves PCI IDs to useful product names.
        try:
            result = subprocess.run(
                ["lspci", "-s", device.name],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            output = result.stdout.strip()

            if output:
                # Example:
                # 03:00.0 VGA compatible controller: Intel Corporation ...
                if ": " in output:
                    gpu_name = output.split(": ", 1)[1]

                    # Remove the controller class prefix.
                    if ": " in gpu_name:
                        gpu_name = gpu_name.split(": ", 1)[1]

        except (OSError, subprocess.SubprocessError):
            pass

        # Fall back to raw PCI IDs if lspci is unavailable.
        if not gpu_name:
            try:
                device_id = int(
                    (device / "device").read_text(encoding="utf-8").strip(),
                    16,
                )
            except (OSError, ValueError):
                device_id = None

            if vendor is not None and device_id is not None:
                gpu_name = f"PCI {vendor:04x}:{device_id:04x}"
            else:
                gpu_name = device.name

        devices.append(gpu_name)

    return {
        "has_nvidia": has_nvidia,
        "has_multiple_gpus": len(devices) >= 2,
        "gpu_count": len(devices),
        "devices": devices,
    }


def _get_init_system_info() -> str:
    """Detect and return the init system being used.
    
    Detection order:
    1. Check if systemd (via is_systemd())
    2. Check ps 1 for runit or openrc
    3. Check if /sbin/init is a symlink (readlink succeeds) vs regular file
    4. If /sbin/init is not a symlink or readlink fails, assume sysvinit
    
    Returns:
        str: Init system name ('systemd', 'sysvinit', 'runit', 'openrc', or 'unknown')
    """
    import os
    import subprocess
    
    # Check for systemd using existing compat detection
    try:
        from .. import compat
        if compat.is_systemd():
            return "systemd"
    except Exception:
        pass
    
    # Check ps 1 for other init systems
    try:
        result = subprocess.run(
            ["ps", "-p", "1", "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=5
        )
        init_process = result.stdout.strip().lower()
        
        if "runit" in init_process:
            return "runit"
        if "openrc" in init_process:
            return "openrc"
    except Exception:
        pass
    
    # Check /sbin/init symlink to determine init system
    try:
        if os.path.islink("/sbin/init"):
            # It's a symlink, check where it points
            target = os.readlink("/sbin/init").lower()
            if "openrc" in target:
                return "openrc"
            if "runit" in target:
                return "runit"
        # If /sbin/init exists and is NOT a symlink, it's likely sysvinit
        if os.path.exists("/sbin/init"):
            return "sysvinit"
    except Exception:
        pass
    
    return "unknown"


def _get_desktop_info() -> dict:
    """Detect the current desktop environment and window manager/compositor."""
    import os
    import subprocess

    desktop = ""
    wm = ""

    # Standard desktop/session variables.
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("XDG_SESSION_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or ""
    ).strip()

    # Normalize common multi-component values such as:
    # XDG_CURRENT_DESKTOP=KDE
    # XDG_CURRENT_DESKTOP=GNOME
    # XDG_CURRENT_DESKTOP=Unity:Unity7
    if desktop:
        desktop = desktop.replace(":", "/")

    # Detect common window managers/compositors from running processes.
    known_wms = (
        ("kwin_wayland", "KWin (Wayland)"),
        ("kwin_x11", "KWin (X11)"),
        ("gnome-shell", "Mutter"),
        ("mutter", "Mutter"),
        ("sway", "Sway"),
        ("hyprland", "Hyprland"),
        ("Hyprland", "Hyprland"),
        ("weston", "Weston"),
        ("xfwm4", "Xfwm4"),
        ("openbox", "Openbox"),
        ("i3", "i3"),
        ("bspwm", "bspwm"),
        ("awesome", "Awesome"),
        ("marco", "Marco"),
        ("cinnamon", "Muffin"),
        ("muffin", "Muffin"),
    )

    try:
        result = subprocess.run(
            ["ps", "-eo", "comm="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )

        processes = {
            process.strip()
            for process in result.stdout.splitlines()
            if process.strip()
        }

        for process, display_name in known_wms:
            if process in processes:
                wm = display_name
                break

    except (OSError, subprocess.SubprocessError):
        pass

    return {
        "desktop": desktop or "unknown",
        "wm": wm or "unknown",
    }


def get_system_context() -> str:
    """Build a system info context string for bug reports."""
    os_info = _get_os_info()
    cpu_model = _get_cpu_model()
    gpu_info = _get_gpu_info()
    init_system = _get_init_system_info()
    desktop_info = _get_desktop_info()

    context_parts = [f"OS: {os_info['id']}"]

    if os_info["version"]:
        context_parts[-1] += f" {os_info['version']}"

    context_parts.append(f"linuxtoys {__version__}")

    if init_system and init_system != "unknown":
        context_parts.append(f"Init: {init_system}")

    if cpu_model != "unknown":
        context_parts.append(f"CPU: {cpu_model}")

    for index, gpu in enumerate(gpu_info["devices"], start=1):
        if gpu_info["gpu_count"] == 1:
            context_parts.append(f"GPU: {gpu}")
        else:
            context_parts.append(f"GPU {index}: {gpu}")
    
    if desktop_info["desktop"] != "unknown":
        context_parts.append(f"Desktop: {desktop_info['desktop']}")
        if desktop_info["wm"] != "unknown":
                context_parts.append(f"Compositor: {desktop_info['wm']}")
    else:
        if desktop_info["wm"] != "unknown":
            context_parts.append(f"WM: {desktop_info['wm']}")

    return " | ".join(context_parts)

def _get_repo_owner_mention(script_name: str | None = None) -> str:
    """
    Return a GitHub @owner mention for an officially supported
    repository-list application.

    If script_name is omitted, infer it from execution history.
    """
    try:
        if script_name is None:
            history = _load_history()
            if not history:
                return ""

            script_name = history[-1].get("name", "").strip()

        if not script_name:
            return ""

        from .. import parser, official_index

        if not official_index.is_verified_name(script_name):
            return ""

        normalized_name = script_name.casefold()

        for entry in parser.get_repo_entries():
            if (
                entry.get("name", "").strip().casefold()
                != normalized_name
            ):
                continue

            repo = entry.get("repo", "").strip()
            if not repo:
                return ""

            parsed = urlparse(repo)

            if parsed.scheme not in ("http", "https"):
                return ""

            if parsed.hostname not in (
                "github.com",
                "www.github.com",
            ):
                return ""

            parts = [
                part
                for part in parsed.path.split("/")
                if part
            ]

            if len(parts) < 2:
                return ""

            owner = parts[0]

            if not owner or not all(
                char.isalnum() or char == "-"
                for char in owner
            ):
                return ""

            return f"@{owner}"

    except Exception:
        return ""

    return ""
    
# --- Script History Management ---
def _load_history() -> list:
    """Load script execution history from file."""
    if not _HISTORY_FILE.exists():
        return []
    try:
        with open(_HISTORY_FILE, "r") as f:
            data = json.load(f)
        return data.get("history", [])
    except Exception:
        return []
 
def _save_history(history: list) -> None:
    """Save script execution history to file."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.parent.chmod(0o700)
        with open(_HISTORY_FILE, "w") as f:
            json.dump({"history": history}, f)
        _HISTORY_FILE.chmod(0o600)
    except Exception:
        pass  # Fail silently to avoid breaking bug reports
 
def add_script_to_history(script_name: str) -> None:
    """Add a script execution to history (keep last 10)."""
    try:
        history = _load_history()
        # Add new entry with timestamp
        history.append({
            "name": script_name,
            "timestamp": time.time()
        })
        # Keep only last 10
        history = history[-10:]
        _save_history(history)
    except Exception:
        pass  # Fail silently
 
def get_history_context() -> str:
    """Get formatted script execution history for bug reports."""
    try:
        history = _load_history()
        if not history:
            return ""
        
        # Format as "Script1, Script2, ..." (last first)
        script_names = [h.get("name", "unknown") for h in reversed(history)]
        return "Recent scripts: " + " → ".join(script_names[:10])
    except Exception:
        return ""


def _get_last_n_lines(text: str, n: int = 20) -> str:
    """Extract the last n lines from a text block."""
    lines = text.strip().split("\n")
    if len(lines) <= n:
        return text
    return "\n".join(lines[-n:])


def _get_transmap_content() -> str:
    """Load and format transmap file content for the report."""
    transmap_path = "/tmp/linuxtoys/transmap"
    try:
        if not Path(transmap_path).exists():
            return ""
        with open(transmap_path, "r") as f:
            content = f.read().strip()
        if not content:
            return ""
        return f"=== TRANSMAP (Operations Log) ===\n{content}\n"
    except Exception:
        return ""


def _get_last_registry_entries(n: int = 2) -> str:
    """Extract the last n script entries from the registry file."""
    registry_path = Path.home() / ".cache" / "linuxtoys" / "registry"
    try:
        if not registry_path.exists():
            return ""
        
        with open(registry_path, "r") as f:
            content = f.read()
        
        if not content.strip():
            return ""
        
        # Split by "---\n" to get individual entries
        entries = content.split("---\n")
        # Reverse and take the last n non-empty entries
        entries = [e.strip() for e in entries if e.strip()]
        entries = entries[-n:]
        
        if not entries:
            return ""
        
        formatted = "=== RECENT REGISTRY (Last Script Executions) ===\n"
        formatted += "\n---\n".join(entries)
        formatted += "\n"
        return formatted
    except Exception:
        return ""
class LogCapture:
    """Tees stdout/stderr into an in-memory buffer AND the real terminal."""
    def __init__(self):
        self._buffer = StringIO()
        self._stdout = sys.stdout
        self._stderr = sys.stderr
 
    def start(self):
        sys.stdout = self
        sys.stderr = self
 
    def stop(self):
        sys.stdout = self._stdout
        sys.stderr = self._stderr
 
    def write(self, msg: str):
        self._buffer.write(msg)
        self._stdout.write(msg)
 
    def flush(self):
        self._stdout.flush()
 
    def get_logs(self) -> str:
        return self._buffer.getvalue()
 
    def clear(self):
        self._buffer = StringIO()
 
log_capture = LogCapture()
_antenna_initialized = False
 
# --- Token management ---
def _strip_control_characters(value: str) -> str:
    """Preserve Unicode text while removing non-printing control characters."""
    return "".join(
        char for char in unicodedata.normalize("NFC", value)
        if char in "\n\r\t" or unicodedata.category(char) not in {"Cc", "Cs"}
    )


_jwt_token: str | None = None
_jwt_expires_at: float = 0
_app_token: str | None = None
 
def _get_cached_app_token() -> str | None:
    """Load the app token from cache if it exists and is valid."""
    if not _SECRET_CACHE.exists():
        return None
    try:
        with open(_SECRET_CACHE, "r") as f:
            data = json.load(f)
        # Verify cache is not too old (e.g., older than 7 days)
        cache_time = data.get("timestamp", 0)
        if time.time() - cache_time > 604800:  # 7 days
            return None
        return data.get("token")
    except Exception:
        return None
 
def _cache_app_token(token: str) -> None:
    """Save the app token to cache."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions (owner read/write only)
        _SECRET_CACHE.parent.chmod(0o700)
        with open(_SECRET_CACHE, "w") as f:
            json.dump({
                "token": token,
                "timestamp": time.time()
            }, f)
        _SECRET_CACHE.chmod(0o600)
    except Exception as e:
        print(f"[IssueReporter] Warning: Could not cache bootstrap token: {e}", file=sys.stderr)
 
def _bootstrap_app_token() -> str:
    """
    Fetch the app token from the server without needing a pre-shared secret.
    Uses machine ID + buildinfo for first-time identification.
    """
    # Try cached token first
    cached = _get_cached_app_token()
    if cached:
        return cached
    
    # Generate a machine identifier (can be customized)
    machine_id = _get_machine_id()
    _cd = _get_creation_day()
    _sig, _st = _sign_machine_id(machine_id)
    
    try:
        resp = requests.post(
            f"{_REPORT_URL}/bootstrap",
            json={"machine_id": machine_id, "signature": _sig, "signature_time": _st, "creation_day": _cd},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["app_token"]
        _cache_app_token(token)
        return token
    except ConnectionError:
        print("[IssueReporter] Bootstrap failed: No internet connection", file=sys.stderr)
        raise
    except Timeout:
        print("[IssueReporter] Bootstrap failed: Connection timeout", file=sys.stderr)
        raise
    except requests.exceptions.HTTPError as e:
        print(f"[IssueReporter] Bootstrap failed: Server error ({e.response.status_code})", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[IssueReporter] Bootstrap failed: {e}", file=sys.stderr)
        raise
 
 
def _get_machine_id() -> str:
    """
    Return a stable, random machine identifier for this installation.
    Generated once on first bootstrap and persisted in the cache file
    alongside the app token — stored in obfuscated form.
    """
    # Try to load an existing machine ID from the cache file
    if _SECRET_CACHE.exists():
        try:
            with open(_SECRET_CACHE, "r") as f:
                data = json.load(f)
            obfuscated_mid = data.get("machine_id_obf")
            if obfuscated_mid:
                return obfuscated_mid
        except Exception:
            pass

    # Generate a new obfuscated machine identifier
    mid = _generate_obfuscated_machine_id()
    obfuscated_mid = _encode_machine_id(mid)
    
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _SECRET_CACHE.parent.chmod(0o700)
        # Merge into existing cache data if present, else start fresh
        existing: dict = {}
        if _SECRET_CACHE.exists():
            try:
                with open(_SECRET_CACHE, "r") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["machine_id_obf"] = obfuscated_mid
        with open(_SECRET_CACHE, "w") as f:
            json.dump(existing, f)
        _SECRET_CACHE.chmod(0o600)
    except Exception:
        pass  # Non-fatal — caller will still get a valid (ephemeral) ID
    return obfuscated_mid

def _generate_obfuscated_machine_id() -> str:
    """Proprietary entropy generation."""
    import os
    _a = os.urandom(8)
    _b = int(time.time() * 1000000).to_bytes(8, byteorder='big')
    try:
        _c = hashlib.sha256(__import__('socket').gethostname().encode()).digest()[:4]
    except:
        _c = os.urandom(4)
    _d = os.urandom(8)
    _e = b"".join([_a, _b, _c, _d])
    return hashlib.sha256(hashlib.sha256(_e).digest() + _e).digest().hex()


def _encode_machine_id(mid: str) -> str:
    """Entropy encoding."""
    _s = hashlib.sha256(mid.encode()).digest()[:8]
    _m = bytes.fromhex(mid)
    return f"{base64.b64encode(_s).decode('ascii')[:8]}:{base64.b64encode(_m).decode('ascii')}"


def _decode_machine_id(obfuscated: str) -> str:
    """Entropy decoding."""
    _p = obfuscated.split(":", 1)
    if len(_p) != 2:
        raise ValueError("Invalid format")
    return base64.b64decode(_p[1]).hex()


def _get_creation_day() -> int:
    """Get or create the installation creation day offset."""
    if _SECRET_CACHE.exists():
        try:
            with open(_SECRET_CACHE, "r") as f:
                data = json.load(f)
            _cd = data.get("creation_day")
            if _cd is not None and isinstance(_cd, int) and _cd >= 0:
                return _cd
        except Exception:
            pass
    
    # Create new creation_day
    _cd = int(time.time() // 86400)
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _SECRET_CACHE.parent.chmod(0o700)
        existing: dict = {}
        if _SECRET_CACHE.exists():
            try:
                with open(_SECRET_CACHE, "r") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["creation_day"] = _cd
        with open(_SECRET_CACHE, "w") as f:
            json.dump(existing, f)
        _SECRET_CACHE.chmod(0o600)
    except Exception:
        pass
    return _cd


def _sign_machine_id(_m: str) -> tuple[str, int]:
    """Generate HMAC signature for machine_id with day offset."""
    try:
        _decoded = _decode_machine_id(_m)
    except Exception:
        raise ValueError("Cannot sign invalid machine_id")
    _d = int(time.time() // 86400)
    _k = b"linuxtoys-antenna-v1"
    _v = f"{_decoded}:{_d}".encode()
    return hmac.new(_k, _v, hashlib.sha256).hexdigest(), _d

 
def _authenticate() -> tuple[str, float]:
    global _app_token
    
    # Get or bootstrap the app token
    if _app_token is None:
        _app_token = _bootstrap_app_token()
    
    try:
        resp = requests.post(
            f"{_REPORT_URL}/auth",
            headers={"X-App-Token": _app_token},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        expires_at = time.time() + data["expires_in"] - 60  # 60s early refresh buffer
        return data["token"], expires_at
    except ConnectionError:
        print("[IssueReporter] Authentication failed: No internet connection", file=sys.stderr)
        raise
    except Timeout:
        print("[IssueReporter] Authentication failed: Connection timeout", file=sys.stderr)
        raise
    except requests.exceptions.HTTPError as e:
        print(f"[IssueReporter] Authentication failed: Server error ({e.response.status_code})", file=sys.stderr)
        raise
 
def _get_token() -> str:
    global _jwt_token, _jwt_expires_at
    if _jwt_token is None or time.time() >= _jwt_expires_at:
        _jwt_token, _jwt_expires_at = _authenticate()
        # Token is in memory only — cleared on process exit
    return _jwt_token
 
# --- Initialization ---
def _initialize_antenna() -> None:
    """Initialize antenna logging and exception hooks."""
    global _antenna_initialized
    if _antenna_initialized:
        return
    
    log_capture.start()
    sys.excepthook = _exception_hook
    _antenna_initialized = True
 
# --- Issue submission ---
def submit_issue(
    title: str,
    logs: str = "",
    context: str = "",
    is_footer_triggered: bool = False,
    related_app: str | None = None,
    infer_related_app: bool = True,
) -> dict | None:
    """Submit a GitHub issue. Logs default to current captured output (last 20 lines).
    
    Args:
        title: Issue title
        logs: Issue logs (defaults to captured output)
        context: System context
        is_footer_triggered: If True, include recent registry entries (for manual reports from footer)
    """
    # Initialize antenna on first bug report submission
    _initialize_antenna()
    
    # Track if logs were explicitly provided (vs captured from stdout)
    logs_explicitly_provided = bool(logs)
    
    if not logs:
        logs = log_capture.get_logs()
    
    # If logs are empty even after getting from log_capture, treat as footer-triggered
    # to include recent registry entries (matches behavior of main menu reports)
    if not logs.strip():
        is_footer_triggered = True
    
    # Only truncate if logs came from log capture (not explicitly provided)
    # This preserves pre-formatted data like registry information or terminal dumps
    if not logs_explicitly_provided:
        logs = _get_last_n_lines(logs, n=20)
    
    # Append transmap content if available
    transmap_content = _get_transmap_content()
    if transmap_content:
        logs = logs + "\n" + transmap_content
    
    # Apply line limit after all content is assembled if it came from log_capture
    # This ensures transmap is never truncated
    if not logs_explicitly_provided and transmap_content:
        # Only apply additional truncation if we have a lot of lines from log_capture + transmap
        total_lines = len(logs.split("\n"))
        if total_lines > 50:
            # Truncate terminal lines but preserve transmap
            lines_list = logs.split("\n")
            transmap_start = next((i for i, l in enumerate(lines_list) if "=== TRANSMAP" in l), len(lines_list))
            # Keep terminal output trimmed, but preserve all transmap content
            if transmap_start > 0:
                terminal_lines = lines_list[:transmap_start]
                terminal_lines = terminal_lines[-15:]  # Keep last 15 lines of terminal output
                transmap_lines = lines_list[transmap_start:]
                logs = "\n".join(terminal_lines + transmap_lines)
    
    # Append recent registry entries only if footer-triggered (useful for manual reports from footer link)
    if is_footer_triggered:
        registry_content = _get_last_registry_entries(n=2)
        if registry_content:
            logs = logs + "\n" + registry_content

    # Handle upstream developer tagging
    validated_app = None
    if related_app:
        try:
            from .. import official_index

            if official_index.is_verified_name(related_app):
                validated_app = related_app
        except Exception:
            pass
    if validated_app:
        context = (
            f"{context}\n\n"
            f"Official application: {validated_app}"
        ).strip()

        repo_owner = _get_repo_owner_mention(validated_app)
    elif infer_related_app:
        repo_owner = _get_repo_owner_mention()
    else:
        repo_owner = ""
    if repo_owner:
        context = (
            f"{context}\n"
            f"Upstream repository maintainer: {repo_owner}"
        ).strip()
        
    # Preserve user language characters while dropping terminal control sequences.
    logs    = _strip_control_characters(logs)
    title   = _strip_control_characters(title).strip()
    context = _strip_control_characters(context).strip()
 
    try:
        resp = requests.post(
            f"{_REPORT_URL}/report-issue",
            headers={
                "Authorization": f"Bearer {_get_token()}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "logs": logs,
                "context": context,
                "upstream_notified": bool(repo_owner),
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"[IssueReporter] Issue #{data['issue_number']} filed: {data['issue_url']}")
        return data
    except ConnectionError:
        print("[IssueReporter] Could not file issue: No internet connection", file=sys.stderr)
        raise
    except Timeout:
        print("[IssueReporter] Could not file issue: Connection timeout", file=sys.stderr)
        raise
    except requests.exceptions.HTTPError as e:
        print(f"[IssueReporter] Could not file issue: Server error ({e.response.status_code})", file=sys.stderr)
        raise
    except Exception as e:
        print(f"[IssueReporter] Could not file issue: {e}", file=sys.stderr)
        raise
 
# --- Auto-submit on unhandled exceptions ---
def _exception_hook(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(tb_str)
    try:
        submit_issue(
            title=f"Unhandled Exception: {exc_type.__name__}: {exc_value}",
            context=tb_str,
        )
    except Exception:
        pass  # Silently fail to avoid infinite recursion
    sys.exit(1)
