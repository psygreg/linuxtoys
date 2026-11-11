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

- **copr/**: Build RPM packages for Fedora/COPR (requires Fedora distrobox container)
- **deb/**: Build DEB packages for Debian/Ubuntu (requires Debian distrobox container)
- **pkg/**: Build AUR packages for Arch Linux (requires Arch distrobox container)
- **appimage/**: Build the universal AppImage via pkgforge quick-sharun

> [!WARNING]
> The distrobox-backed targets (`copr/`, `deb/`, `pkg/`) require their matching container to be correctly configured with all dependencies installed for the build to succeed.
