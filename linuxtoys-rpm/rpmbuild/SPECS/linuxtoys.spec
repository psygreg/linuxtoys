Name:           linuxtoys
Version:        1.7.1
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash newt curl wget
BuildRequires:  desktop-file-utils

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/bin
install -m 755 linuxtoys.sh %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/applications
desktop-file-install --dir=%{buildroot}/usr/share/applications LinuxToys.desktop
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps
install -m 644 linuxtoys.png %{buildroot}/usr/share/icons/hicolor/scalable/apps/

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
/usr/bin/linuxtoys.sh
/usr/share/applications/LinuxToys.desktop
/usr/share/icons/hicolor/scalable/apps/linuxtoys.png

%changelog
* Wed May  21 2025 Victor Gregory <psygreg@pm.me> - 1.7.1
- Improved grub-btrfs setup with basic snapper configuration
- Automatic updater implemented