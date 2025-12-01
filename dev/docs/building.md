## Prerequisites

### Automated Dependency Installation
You can automatically install all required dependencies for your distribution using the provided script:

```bash
# From the project root
./dev/scripts/install_packages.sh
```

This script detects your package manager (dnf, apt, pacman, zypper) and installs the necessary packages.

### Manual Prerequisites (Reference)

#### For DEB packages:
- `devscripts` package installed
- Debian/Ubuntu-based system or container

#### For RPM packages:
- `rpmbuild` installed
- Fedora/RHEL-based system or container
- Script is configured for Silverblue (copies rpmbuild to $HOME)

#### For Arch packages:
- `base-devel` group installed
- Arch Linux system or container

### For AppImage

You'll need to install linuxdeploy tools. The scripts will download them automatically, but you can also install them manually:

```bash
# Download linuxdeploy
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage
# Download linuxdeploy Python plugin
wget https://github.com/niess/linuxdeploy-plugin-python/releases/download/continuous/linuxdeploy-plugin-python-x86_64.AppImage
chmod +x linuxdeploy-plugin-python-x86_64.AppImage
```

### Python Dependencies

Informed in the `requirements.txt` file:

```
# p3/requirements.txt
requests>=2.25.0
urllib3>=1.26.0
certifi>=2021.5.25
```

## Usage

### Individual package builds:

1. **DEB package:**
   ```bash
   cd deb
   ./builddeb.sh
   ```

2. **RPM package:**
   ```bash
   cd rpm
   ./buildrpm.sh
   ```

3. **Arch package:**
   ```bash
   cd pkgbuild
   ./buildpkg.sh
   ```
4. **AppImage:**
Should be built in Ubuntu LTS!

- Dependency check:
   ```bash
   cd appimage
   ./appimagedeps.sh
   ```

- Packaging:
   ```bash
   cd appimage
   ./buildappimage.sh
   ```

## Package structure:

- Main executable: `/usr/bin/linuxtoys`
- Application files: `/usr/bin/linuxtoys/` (contains the Python app)
- Desktop file: `/usr/share/applications/LinuxToys.desktop`
- Icon: `/usr/share/icons/hicolor/scalable/apps/linuxtoys.png`

## Dependencies

### System Dependencies

The required system packages vary by distribution. The `install_packages.sh` script handles this automatically, but here are the lists for reference:

**Fedora/RHEL (dnf):**
```
python3 python3-devel zenity jq gobject-introspection-devel cairo-devel cairo cairo-gobject-devel gtk3 curl wget git vte291 gcc pkg-config
```

**Debian/Ubuntu (apt):**
```
python3 python3-dev zenity jq libgirepository1.0-dev libcairo2-dev libcairo2 libcairo-gobject2 libgtk-3-dev curl wget git libvte-2.91-dev gcc pkg-config
```

**Arch Linux (pacman):**
```
python zenity jq gobject-introspection cairo gtk3 curl wget git vte3 gcc pkgconf
```

**OpenSUSE (zypper):**
```
python3 python3-devel zenity jq gobject-introspection-devel cairo-devel cairo cairo-gobject-devel gtk3 curl wget git vte291 gcc pkg-config
```

### Python Dependencies

These are installed via `pip` (usually in a venv) or system packages if available:

```
PyGObject>=3.36.0
requests>=2.25.0
urllib3>=1.26.0
certifi>=2021.5.25
```

## Output files:

- **DEB:** `deb/linuxtoys_<version>-1_amd64.deb`
- **RPM:** `~/rpmbuild/RPMS/x86_64/linuxtoys-<version>-1.x86_64.rpm`
- **Arch:** `pkgbuild/linuxtoys-bin-<version>-1-x86_64.pkg.tar.zst`
- **Arch tarball for AUR:** `pkgbuild/linuxtoys-<version>.tar.xz`
