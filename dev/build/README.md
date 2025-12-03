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

> [!WARNING]
> For the `build_all.sh` script to work correctly, you must have at least 3 **Distrobox** containers created: **Arch Linux**, **Debian**, and **Fedora**. All 3 containers must be correctly configured with all dependencies installed for the build to succeed.
