# Developer Documentation

Welcome to the **LinuxToys** developer documentation. This guide provides everything you need to know to contribute to the project, build packages, and release updates.

---

## Getting Started

### Prerequisites

To develop for LinuxToys, you need a Linux environment with the necessary build tools. We provide a library to help install dependencies, but please note the warning below.

> [!WARNING]
> The `dev/libs/install_all_packages.lib` library is currently in **TEST MODE**. Use it with caution.

### Setting up the Environment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/psygreg/linuxtoys.git
    cd linuxtoys
    ```

2.  **Install Dependencies:**
    You can inspect and use the `dev/libs/install_all_packages.lib` to identify and install packages for your distribution (Fedora, Debian/Ubuntu, Arch, OpenSUSE).

    **Common System Dependencies:**
    - Python 3.13+
    - GTK3 & Cairo development headers
    - `rpmbuild` (for RPM)
    - `devscripts` (for DEB)
    - `base-devel` (for Arch)

    **Python Dependencies:**
    Found in `p3/requirements.txt`:
    - `requests`
    - `urllib3`
    - `certifi`
    - `PyGObject`

---

## Build System

The build system is located in `dev/build`.

### Global Build Script

> [!WARNING]
> For `dev/build/build_all.sh` to work correctly, you must have at least 3 **Distrobox** containers created: **Arch Linux**, **Debian**, and **Fedora**. All 3 containers must be correctly configured with all dependencies installed for the build to succeed.

To attempt building all packages:
```bash
cd dev/build
./build_all.sh
```

### Individual Package Builds

You can build specific packages by navigating to their respective directories in `dev/build`:

-   **DEB (Debian/Ubuntu):**
    ```bash
    cd dev/build/deb
    ./build.sh
    ```

-   **RPM (Fedora/RHEL/OpenSUSE):**
    ```bash
    cd dev/build/rpm
    ./build.sh
    ```

-   **Arch Linux (PKGBUILD):**
    ```bash
    cd dev/build/pkg
    ./build.sh
    ```

-   **COPR:**
    ```bash
    cd dev/build/copr
    ./build.sh
    ```

-   **Nuitka:**
    ```bash
    cd dev/build/nuitka
    ./build.sh
    ```

### Development Guidelines

-   **Path Handling**: Always use `ROOT_DIR` in scripts to avoid relative path issues (`cd ./` or `../`).
-   **Logging**: Use the `_msg` function from `dev/libs/utils.lib` for outputting logs.
    ```bash
    source "$ROOT_DIR/dev/libs/utils.lib"
    _msg "Your log message"
    ```
---

## Directory Structure

-   `dev/build`: Build scripts for different package formats.
-   `dev/libs`: Shared libraries and functions (e.g., `utils.lib`, `install_all_packages.lib`).
-   `dev/docs`: Developer documentation.
-   `dev/build_output`: Directory where built artifacts are stored.

> [!NOTE]
> Each root folder (`dev/libs` and `dev/build`) contains a dedicated `README.md` file with more detailed information and specific instructions for developers.

