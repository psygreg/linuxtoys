Name:           linuxtoys
Version:        5.6.2
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash git curl wget zenity python3 python3-gobject gtk3 python3-requests python3-urllib3 python3-certifi vte291
BuildRequires:  desktop-file-utils

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%global debug_package %{nil}

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/linuxtoys/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
mkdir -p %{buildroot}/usr/share/applications/

# Install the main executable script
install -m 755 usr/bin/linuxtoys %{buildroot}/usr/bin/
install -m 755 usr/bin/linuxtoys-cli %{buildroot}/usr/bin/

# Install the Python application directory with all subdirectories
cp -rf usr/share/linuxtoys/* %{buildroot}/usr/share/linuxtoys/

# Set proper permissions for executable files
chmod +x %{buildroot}/usr/share/linuxtoys/run.py
find %{buildroot}/usr/share/linuxtoys/scripts/ -name "*.sh" -exec chmod +x {} \;
find %{buildroot}/usr/share/linuxtoys/helpers/ -name "*.sh" -exec chmod +x {} \;

# Install icon and desktop file
install -m 644 usr/share/icons/hicolor/scalable/apps/linuxtoys.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/
desktop-file-install --dir=%{buildroot}/usr/share/applications usr/share/applications/LinuxToys.desktop

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
/usr/bin/linuxtoys
/usr/bin/linuxtoys-cli
/usr/share/linuxtoys
/usr/share/icons/hicolor/scalable/apps/linuxtoys.svg
/usr/share/applications/LinuxToys.desktop

%changelog
* Mon Oct 20 2025 Victor Gregory <psygreg@pm.me> - 5.5.1
- Updated to current app structure with full Python application
- Added proper file permissions for all scripts
- Updated dependencies for current requirements
