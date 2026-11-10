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
- **solus/**: Build .eopkg packages for Solus OS (uses solbuild)
- **nuitka/**: Build standalone executable using Nuitka

## Solus Package Building

For Solus OS, use the dedicated `solus/` directory. See [solus/README.md](solus/README.md) for detailed instructions on building .eopkg packages locally or via CI.

> [!WARNING]
> For the `build_all.sh` script to work correctly, you must have at least 3 **Distrobox** containers created: **Arch Linux**, **Debian**, and **Fedora**. All 3 containers must be correctly configured with all dependencies installed for the build to succeed. Solus builds can be performed separately using the CI pipeline or locally using solbuild.

## Native source qualification (ARM64 M2)

Build on the target Linux architecture; macOS and emulation do not qualify Linux
runtime behavior. Record `python3 --version`, `rustc --version`, `cargo --version`
and `uname -m`. Use the existing Cargo lockfile and Python pins unchanged.
The detailed tested environment, staged Ubuntu package versions and limitations
are in [ARM64-QUALIFICATION.md](../ARM64-QUALIFICATION.md).

The native GTK build needs a C linker, `pkg-config` and GTK3 development metadata
(`libgtk-3-dev` and its native dependencies on Ubuntu). Runtime probes need
PyGObject, GTK3/VTE typelibs, AppStream 1.0 typelib, PyCairo and its GI bridge
(`python3-gi-cairo`). An installed GTK runtime alone does not supply build files.
Maturin is the existing build frontend; the tested tool was 1.9.4. Do not replace
an installed dependency to resolve a failure without first recording the cause.

From a disposable source checkout with those prerequisites available:

```bash
export CARGO_TARGET_DIR="$(pwd)/target-native"
./build-rust.sh develop --debug
cargo test --locked --workspace
python3 -m unittest discover -s dev/tests -v
PYTHONPATH=p3:p3/vendor python3 dev/tests/native_application_smoke.py imports \
  --profile /tmp/linuxtoys-import-profile
GDK_BACKEND=wayland PYTHONPATH=p3:p3/vendor \
  dbus-run-session -- python3 dev/tests/native_application_smoke.py launcher \
  --profile /tmp/linuxtoys-wayland-profile
GDK_BACKEND=x11 PYTHONPATH=p3:p3/vendor \
  dbus-run-session -- python3 dev/tests/native_application_smoke.py launcher \
  --profile /tmp/linuxtoys-x11-profile
```

Each profile must be new. The probes disable automatic updates in that profile
and decline setup/install prompts. A display socket and authorization for the
requested backend must actually exist; report absence rather than silently using
another backend. `widgets`, `gui`, `tui` and `mcp` probes are also available.
Inspect both built libraries with `readelf -h` and their dependencies with `ldd`.
`develop` removes stale extension variants before copying its freshly built ones.

`native_font_smoke.py NEW_OUTPUT_DIRECTORY` downloads and tests the three fonts
only inside that new directory. `--asset-cache DIRECTORY` is explicit test-only
replay of previously downloaded artifacts; production validation remains active.
`dev/tests/no_network.c` provides process-scoped connection fault injection for
optional-backend/offline probes; it is not a network security boundary. Never
install test artifacts or run package-release commands as part of these probes.
