Name:           linuxtoys
Version:        7.3
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash git curl wget zenity appstream appstream-data python3 python3-gobject gtk3 python3-requests python3-urllib3 python3-certifi vte291 /usr/bin/script (sudo or sudo-rs)
BuildRequires:  desktop-file-utils cargo rust python3-devel maturin gtk3-devel pkgconf-pkg-config patchelf

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%global debug_package %{nil}

%prep
%setup -q

%build
mkdir -p target/wheels/catalog
(cd src/catalog-rs && maturin build --release --locked --out ../../target/wheels/catalog)
cargo build --release --locked --manifest-path src/gui-rs/Cargo.toml
CATALOG_WHEEL=$(find target/wheels/catalog -maxdepth 1 -type f -name '*.whl' -print -quit)
test -n "$CATALOG_WHEEL"
rm -rf wheel-unpack-catalog
python3 -m zipfile -e "$CATALOG_WHEEL" wheel-unpack-catalog
test -n "$(find wheel-unpack-catalog -type f -name '_catalog_rs*.so' -print -quit)"
test -f target/release/liblinuxtoys_gui.so

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/linuxtoys/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
mkdir -p %{buildroot}/usr/share/applications/

cp -a p3/. %{buildroot}/usr/share/linuxtoys/
find %{buildroot}/usr/share/linuxtoys -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find %{buildroot}/usr/share/linuxtoys -type f -name '*.pyc' -delete 2>/dev/null || true

CATALOG_EXTENSION=$(find wheel-unpack-catalog -type f -name '_catalog_rs*.so' -print -quit)
GUI_LIBRARY=target/release/liblinuxtoys_gui.so
test -n "$CATALOG_EXTENSION"
test -f "$GUI_LIBRARY"
install -m 755 "$CATALOG_EXTENSION" %{buildroot}/usr/share/linuxtoys/app/$(basename "$CATALOG_EXTENSION")
install -m 755 "$GUI_LIBRARY" %{buildroot}/usr/share/linuxtoys/app/liblinuxtoys_gui.so

cat > %{buildroot}/usr/bin/linuxtoys <<'LAUNCHER'
#!/bin/bash
export LINUXTOYS_PROCESS_NAME="linuxtoys"
if [ "$#" -eq 1 ] && [[ "$1" == linuxtoys://* ]]; then
    unset EASY_CLI
elif [ "$#" -gt 0 ]; then
    export EASY_CLI=1
fi
cd /usr/share/linuxtoys
exec /usr/bin/python3 linuxtoys.py "$@"
LAUNCHER
chmod 755 %{buildroot}/usr/bin/linuxtoys
chmod +x %{buildroot}/usr/share/linuxtoys/linuxtoys.py
find %{buildroot}/usr/share/linuxtoys/scripts/ -name '*.sh' -exec chmod +x {} \;

install -m 644 src/linuxtoys.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/
desktop-file-install --dir=%{buildroot}/usr/share/applications src/LinuxToys.desktop

test -f %{buildroot}/usr/share/linuxtoys/app/_catalog_rs.abi3.so
test -f %{buildroot}/usr/share/linuxtoys/app/liblinuxtoys_gui.so

%files
%defattr(-, root, root, -)
/usr/bin/linuxtoys
/usr/share/linuxtoys
/usr/share/icons/hicolor/scalable/apps/linuxtoys.svg
/usr/share/applications/LinuxToys.desktop

%changelog
* Sat Sep 26 2026 Victor Gregory <psygreg@pm.me> - 7.3
- Added proper file permissions for all scripts
- Updated dependencies for current requirements
