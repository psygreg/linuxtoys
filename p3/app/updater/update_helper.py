import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import shlex

from . import __version__


def get_current_version():
    """Read the installed version from the LinuxToys CLI when available."""
    try:
        result = subprocess.run(
            ["linuxtoys", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        version = result.stdout.strip()
        if re.fullmatch(r"\d+(?:\.\d+){1,2}", version):
            return version
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return __version__

class UpdateHelper:
    def __init__(self):
        self._current_ver = get_current_version()
        self._latest_ver = {}

    def _update_available(self) -> bool:
        if not os.environ.get("DEV_MODE") == "1":
            if not self._is_from_repository():
                return self._check_for_updates()

        return False

    def _check_for_updates(self) -> bool:
        self._latest_ver = self._get_latest_version()

        return self._compare_versions(
            self._current_ver, self._latest_ver.get("tag_name", "")
        ) == 1

    def _compare_versions(self, current, latest) -> int:
        """
        Compare two version strings.
        Returns:
        - 1 if latest > current (update available)
        - 0 if latest == current (up to date)
        - -1 if latest < current (current is newer)
        """

        def version_tuple(v):
            # Convert version string to tuple of integers for comparison
            # e.g., "4.3.1" -> (4, 3, 1), "4.3" -> (4, 3, 0)
            parts = v.split(".")
            return tuple(int(part) for part in parts) + (0,) * (3 - len(parts))

        try:
            current_tuple = version_tuple(current)
            latest_tuple = version_tuple(latest)

            if latest_tuple > current_tuple:
                return 1
            elif latest_tuple == current_tuple:
                return 0
            else:
                return -1
        except (ValueError, TypeError):
            # If version parsing fails, assume no update needed
            return 0

    def _get_latest_version(self, repo_owner="psygreg", repo_name="linuxtoys") -> dict:
        """
        Fetch the latest release info from GitHub API first, with fallback to Gitea.
        Returns dict with tag_name and body if successful, empty dict otherwise.
        """
        # Try GitHub first
        github_url = (
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        )
        result = self._fetch_from_api(github_url, "GitHub")

        if result and result.get("tag_name"):
            return result

        # Fallback to Gitea server
        gitea_url = f"https://git.linux.toys/api/v1/repos/{repo_owner}/{repo_name}/releases/latest"
        result = self._fetch_from_api(gitea_url, "Gitea")

        if result and result.get("tag_name"):
            return result

        # If both fail, return empty dict
        return {"tag_name": "", "body": ""}

    def _fetch_from_api(self, api_url: str, source_name: str) -> dict:
        """
        Fetch release information from the given API URL.
        Returns dict with tag_name and body if successful, None otherwise.
        """
        try:
            request = urllib.request.Request(api_url)
            request.add_header("User-Agent", "LinuxToys-UpdateChecker/1.0")

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return {
                        "tag_name": data.get("tag_name", "").lstrip("v"),
                        "body": data.get("body", ""),
                    }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Release not found on {source_name} (404)")
            else:
                print(f"HTTP error from {source_name}: {e.code}")
            return None
        except urllib.error.URLError as e:
            print(f"Connection error to {source_name}: {e.reason}")
            return None
        except json.JSONDecodeError:
            print(f"Invalid JSON response from {source_name}")
            return None
        except Exception as e:
            print(f"Error fetching from {source_name}: {e}")
            return None

    def __is_from_git(self, path=".") -> bool:
        try:
            return (
                subprocess.call(
                    ["git", "-C", path, "status"],
                    stderr=subprocess.STDOUT,
                    stdout=open(os.devnull, "w"),
                )
                == 0
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def __is_from_ppa(self) -> bool:
        try:
            return any(
                list(
                    filter(
                        lambda f: "linuxtoys" in f,
                        os.listdir("/etc/apt/sources.list.d/"),
                    )
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def __is_from_copr(self) -> bool:
        try:
            return any(
                list(
                    filter(
                        lambda f: "linuxtoys" in f,
                        os.listdir("/etc/yum.repos.d/"),
                    )
                )
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def _is_from_repository(self):
        return (
            self.__is_from_ppa()
            or self.__is_from_copr()
            or self.__is_from_git(os.path.dirname(__file__))
        )


def get_latest_release_version() -> str | None:
    """Return the latest published LinuxToys release version, or None on failure."""
    helper = UpdateHelper()
    latest = helper._get_latest_version().get("tag_name", "").strip()
    return latest or None


def is_current_version(version: str | None = None) -> tuple[bool, str | None]:
    """Return whether *version* matches the latest published LinuxToys release.

    DEV_MODE bypasses the release guard. If the release lookup fails, fail open so
    bug reporting remains available during network/update-service outages.
    """
    if os.environ.get("DEV_MODE") == "1":
        return True, None

    current = (version or __version__).strip()
    latest = get_latest_release_version()
    if not latest:
        return True, None

    helper = UpdateHelper()
    return helper._compare_versions(current, latest) != 1, latest


def run_background_update():
    """Install the latest LinuxToys release without opening the VTE viewer.

    Keep LinuxToys' normal sudo_rq pre-authentication on systems that may need
    native package operations, but bypass it on SteamOS where install.sh uses
    the user-level AppImage/Gear Lever update path. Returns
    (success, error_message).
    """
    script_dir = os.environ.get("SCRIPT_DIR")

    is_steamos = False
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as os_release:
            for line in os_release:
                if line.startswith("ID="):
                    os_id = line.split("=", 1)[1].strip().strip('\"\'')
                    is_steamos = os_id == "steamos"
                    break
    except OSError:
        pass

    if is_steamos:
        script = (
            "#!/usr/bin/env bash\n"
            "curl -fsSL https://linux.toys/install.sh | bash\n"
        )
    else:
        if not script_dir:
            return False, "SCRIPT_DIR environment variable is not set."

        library_path = os.path.join(script_dir, "libs", "linuxtoys.bash")
        if not os.path.isfile(library_path):
            return False, f"LinuxToys shell library was not found: {library_path}"

        script = (
            "#!/usr/bin/env bash\n"
            f"source {shlex.quote(library_path)}\n"
            "sudo_rq\n"
            "\n"
            # Keep install.sh in the same shell that ran sudo_rq. In the\n"
            # background updater there is no controlling TTY, so spawning a\n"
            # separate `bash` via a pipe can make sudo's cached authorization\n"
            # unavailable to the installer.\n"
            "_lt_installer=$(mktemp \"${TMPDIR:-/tmp}/linuxtoys-installer.XXXXXX\") || exit 1\n"
            "trap 'rm -f -- \"$_lt_installer\"' EXIT\n"
            "curl -fsSL https://linux.toys/install.sh -o \"$_lt_installer\" || exit 1\n"
            "source \"$_lt_installer\"\n"
        )

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            prefix="linuxtoys-background-update-",
            suffix=".sh",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(script)
            script_path = tmp.name

        os.chmod(script_path, 0o700)

        with open(os.devnull, "r") as devnull:
            result = subprocess.run(
                ["bash", script_path],
                stdin=devnull,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy(),
            )

        if result.returncode == 0:
            return True, ""

        if result.returncode == 100:
            return False, "Update authentication was cancelled."

        error = (result.stderr or result.stdout or "").strip()
        if not error:
            error = f"Background updater exited with status {result.returncode}."
        return False, error

    except Exception as exc:
        return False, str(exc)
    finally:
        if script_path:
            try:
                os.remove(script_path)
            except OSError:
                pass
