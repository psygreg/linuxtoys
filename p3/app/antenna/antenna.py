import re
import sys
import time
import traceback
import requests
from requests.exceptions import ConnectionError, Timeout
import json
import os
from io import StringIO
from pathlib import Path

_REPORT_URL = "https://bug.linux.toys"

# Cache directory for storing the generated secret (in user's config dir)
_CACHE_DIR = Path.home() / ".cache" / "linuxtoys" / "antenna"
_SECRET_CACHE = _CACHE_DIR / "bootstrap.json"

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

# --- Log capture ---
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
    """Generate a unique machine identifier."""
    import hashlib
    # You can customize this - combine hostname, distro info, etc.
    hostname = os.environ.get("HOSTNAME", "unknown")
    user = os.environ.get("USER", "unknown")
    machine_sig = f"{hostname}:{user}".encode()
    return hashlib.sha256(machine_sig).hexdigest()[:16]


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

def submit_issue(title: str, logs: str = "", context: str = "") -> dict | None:
    """Submit a GitHub issue. Logs default to current captured output."""
    # Initialize antenna on first bug report submission
    _initialize_antenna()
    
    if not logs:
        logs = log_capture.get_logs()

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
