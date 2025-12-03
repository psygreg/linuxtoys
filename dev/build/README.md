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

> [!WARNING!]
> The `build_all.sh` script may NOT work as it is still in test mode. Additionally, the packages required for compilation might not be available in the package manager of the operating system you are using.
