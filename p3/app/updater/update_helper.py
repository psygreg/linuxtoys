import json, subprocess, os, json, re
from . import __version__
import urllib.request
import urllib.error


class UpdateHelper():
    def __init__(self):
        self._current_ver = __version__
        self._latest_ver = {}

    def _update_available(self) -> bool:
        if not os.environ.get('DEV_MODE') == '1':
            if not self._is_from_repository():
                return self._check_for_updates()

        return False

    def _check_for_updates(self) -> bool:
        self._latest_ver = self._get_latest_version()

        if self._compare_versions(self._current_ver, self._latest_ver.get("tag_name", "")):
            return True
        else:
            return False

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
            parts = v.split('.')
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
        Fetch the latest release info from GitHub API.
        Returns dict with tag_name and body if successful, None otherwise.
        """
        try:
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
            request = urllib.request.Request(api_url)
            """
            User-Agent:
            https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api?apiVersion=2022-11-28#user-agent
            """
            request.add_header('User-Agent', 'LinuxToys-UpdateChecker/1.0')

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    return {
                        "tag_name": data.get('tag_name', '').lstrip('v'),
                        "body": data.get('body', '')
                    }
        except Exception as e:
            print(f"Error fetching latest release: {e}")
            return {"tag_name": "", "body": ""}

    def __is_from_git(self, path='.') -> bool:
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
        return self.__is_from_ppa() or self.__is_from_copr() or self.__is_from_git(os.path.dirname(__file__))
