Name:           linuxtoys
Version:        5.6.15
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash git curl wget zenity gtk3 vte291
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

# Install the main executable wrapper script
install -m 755 usr/bin/linuxtoys %{buildroot}/usr/bin/

# Install the Nuitka compiled binary
install -m 755 usr/share/linuxtoys/linuxtoys.bin %{buildroot}/usr/share/linuxtoys/

# Install icon and desktop file
install -m 644 usr/share/icons/hicolor/scalable/apps/linuxtoys.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/
desktop-file-install --dir=%{buildroot}/usr/share/applications usr/share/applications/LinuxToys.desktop

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
/usr/bin/linuxtoys
/usr/share/linuxtoys/linuxtoys.bin
/usr/share/icons/hicolor/scalable/apps/linuxtoys.svg
/usr/share/applications/LinuxToys.desktop

%changelog
* Wed Mar 11 2026 Victor Gregory <psygreg@pm.me> - 5.6.15
- Updated to Nuitka-compiled binary for improved performance
- Removed Python runtime dependency
- Single self-contained executable
