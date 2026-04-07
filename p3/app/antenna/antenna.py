import re
import sys
import time
import traceback
import requests
from requests.exceptions import ConnectionError, Timeout
import json
from io import StringIO
from pathlib import Path
 
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
 
def _get_gpu_info() -> dict:
    """Get GPU information - whether Nvidia is present and total GPU count."""
    try:
        # Import compat module to use existing GPU detection
        from .. import compat
        gpu_keys = compat.get_gpu_compat_keys()
        
        has_nvidia = "gpu-nvidia" in gpu_keys
        gpu_count = len([k for k in gpu_keys if k.startswith("gpu-")])
        has_multiple_gpus = gpu_count >= 2
        
        return {
            "has_nvidia": has_nvidia,
            "has_multiple_gpus": has_multiple_gpus,
            "gpu_count": gpu_count,
        }
    except Exception:
        return {
            "has_nvidia": False,
            "has_multiple_gpus": False,
            "gpu_count": 0,
        }
 
def get_system_context() -> str:
    """Build a system info context string for bug reports."""
    os_info = _get_os_info()
    gpu_info = _get_gpu_info()
    
    context_parts = [f"OS: {os_info['id']}"]
    
    if os_info["version"]:
        context_parts[-1] += f" ({os_info['version']})"
    
    if gpu_info["has_nvidia"]:
        context_parts.append("GPU: Nvidia detected")
    
    if gpu_info["has_multiple_gpus"]:
        context_parts.append(f"Multiple GPUs: {gpu_info['gpu_count']} detected")
    
    return " | ".join(context_parts)
 
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
_NON_PRINTABLE = re.compile(r"[^\x20-\x7E\n\r\t]")
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
    
    try:
        resp = requests.post(
            f"{_REPORT_URL}/bootstrap",
            json={"machine_id": machine_id},
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
    alongside the app token — no env vars, no collisions.
    """
    import uuid
    # Try to load an existing machine ID from the cache file
    if _SECRET_CACHE.exists():
        try:
            with open(_SECRET_CACHE, "r") as f:
                data = json.load(f)
            mid = data.get("machine_id")
            if mid and re.match(r"^[a-f0-9]{32}$", mid):
                return mid
        except Exception:
            pass
 
    # Generate a new random UUID (no host/user info)
    mid = uuid.uuid4().hex  # 32 lowercase hex chars
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
        existing["machine_id"] = mid
        with open(_SECRET_CACHE, "w") as f:
            json.dump(existing, f)
        _SECRET_CACHE.chmod(0o600)
    except Exception:
        pass  # Non-fatal — caller will still get a valid (ephemeral) ID
    return mid
 
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
def submit_issue(title: str, logs: str = "", context: str = "", is_footer_triggered: bool = False) -> dict | None:
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
    
    # Strip non-printable characters client-side before sending
    logs    = _NON_PRINTABLE.sub("", logs)
    title   = _NON_PRINTABLE.sub("", title).strip()
    context = _NON_PRINTABLE.sub("", context).strip()
 
    try:
        resp = requests.post(
            f"{_REPORT_URL}/report-issue",
            headers={
                "Authorization": f"Bearer {_get_token()}",
                "Content-Type": "application/json",
            },
            json={"title": title, "logs": logs, "context": context},
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
