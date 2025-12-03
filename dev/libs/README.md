# Libraries Documentation

This directory is reserved exclusively for **libraries and functions**. Please do not place executable scripts or other types of files here.

## Development Instructions

If you modify any script or create new ones, it is **OBLIGATORY** to always use `ROOT_DIR` to avoid commands like `cd ./` or `../`, as this can complicate development and pollute the code.

If you need to output logs, you must use the `_msg` function by sourcing:
`source "$ROOT_DIR/dev/libs/utils.lib"`

## Warnings

> [!WARNING]
> The `install_all_packages.lib` library is currently in **TEST MODE**. Use it with caution as it may undergo significant changes or contain unstable features.
