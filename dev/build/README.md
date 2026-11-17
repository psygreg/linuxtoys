# Build System Documentation

This directory is reserved exclusively for **build scripts**. Please do not place libraries or other types of files here.

## Development Instructions

If you modify any script or create new ones, it is **OBLIGATORY** to always use `ROOT_DIR` to avoid commands like `cd ./` or `../`, as this can complicate development and pollute the code.

If you need to output logs, you must use the `_msg` function by sourcing:
`source "$ROOT_DIR/dev/libs/utils.lib"`

## For Usage

All `build.sh` files are automated CLI scripts to build the respective systems.

**Example usage:**
```bash
bash build.sh (version) (path)
```

## Build Targets

- **copr/**: Build RPM packages for Fedora/COPR (requires Fedora distrobox container). Builds natively on x86_64 and aarch64 hosts — the spec's `ExclusiveArch` declares both and `rpmbuild` refuses anything else; the binary package always carries the build host's architecture.
- **deb/**: Build DEB packages for Debian/Ubuntu (requires Debian distrobox container). `build.sh --binary-only <version> <output>` prepares the standard source tree but builds only the native binary package (no source upload, no Launchpad duplicate guard, no dput) — the release-workflow path for the second architecture leg. `build.sh --native <version> <output>` builds a local native-only DEB on this host instead (no signing/upload) — the ARM64 development build path: the host must be Linux with a matching dpkg architecture, the reviewed script bundle must validate, and the finished package is payload-verified (`package.py` + `architecture_cli.py`). `debian/control` declares `Architecture: any`, so a source upload to the PPA produces binaries for every architecture enabled there.
- **pkg/**: Build AUR packages for Arch Linux (requires Arch distrobox container). The PKGBUILD `arch` array covers `x86_64` and `aarch64`; the binary package name follows the build host's CARCH.
- **appimage/**: Build the universal AppImage via pkgforge quick-sharun. The artifact name is pinned from the build host's `uname -m` (`LinuxToys-<v>-<arch>.AppImage`); quick-sharun downloads arch-matched sharun/appimagetool artifacts with pinned checksums.

> [!WARNING]
> The distrobox-backed targets (`copr/`, `deb/`, `pkg/`) require their matching container to be correctly configured with all dependencies installed for the build to succeed.
>
> The AppImage target additionally requires the **Arch build host/container** to have `python-requests` and `python-gobject` installed: `DEPLOY_PYTHON` makes quick-sharun copy the host's `/usr/lib/python3.x` (site-packages included) into the AppImage, so the host's Python environment is what users get. `dev/build/appimage/build.sh` verifies both packages before and after deployment.
