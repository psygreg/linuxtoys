## Prerequisites

### For DEB packages:
- `devscripts` package installed
- Debian/Ubuntu-based system or container

### For RPM packages:
- `rpmbuild` installed
- Fedora/RHEL-based system or container
- Script is configured for Silverblue (copies rpmbuild to $HOME)

### For Arch packages:
- `base-devel` group installed
- Arch Linux system or container

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

## Package structure:

- Main executable: `/usr/bin/linuxtoys`
- Application files: `/usr/bin/linuxtoys/` (contains the Python app)
- Desktop file: `/usr/share/applications/LinuxToys.desktop`
- Icon: `/usr/share/icons/hicolor/scalable/apps/linuxtoys.png`

## Dependencies:

All packages depend on:
- `python3` (for running the application)
- `jq` (for handling json translation files)
- `python-gobject`, `python-cairo`, `gtk3` (for GUI)
- `bash` (for the wrapper script)
- `zenity` (for GUI dialogs)
- `curl`, `wget`, `git` (for various tools within LinuxToys)

## Output files:

- **DEB:** `deb/linuxtoys_<version>-1_amd64.deb`
- **RPM:** `~/rpmbuild/RPMS/x86_64/linuxtoys-<version>-1.x86_64.rpm`
- **Arch:** `pkgbuild/linuxtoys-bin-<version>-1-x86_64.pkg.tar.zst`
- **Arch tarball for AUR:** `pkgbuild/linuxtoys-<version>.tar.xz`
