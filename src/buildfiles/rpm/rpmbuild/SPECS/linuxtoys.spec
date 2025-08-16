Name:           linuxtoys
Version:        4.3
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash git curl wget zenity python3 python3-gobject python3-cairo-devel gtk3 jq
BuildRequires:  desktop-file-utils

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%global debug_package %{nil}

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/bin/linuxtoys/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
mkdir -p %{buildroot}/usr/share/applications/

# Install the main executable
install -m 755 usr/bin/linuxtoys %{buildroot}/usr/bin/

# Install the Python application directory
cp -rf usr/bin/linuxtoys/* %{buildroot}/usr/bin/linuxtoys/

# Install icon and desktop file
install -m 644 usr/share/icons/hicolor/scalable/apps/linuxtoys.png %{buildroot}/usr/share/icons/hicolor/scalable/apps/
desktop-file-install --dir=%{buildroot}/usr/share/applications usr/share/applications/LinuxToys.desktop
desktop-file-install --dir=%{buildroot}/usr/share/applications LinuxToys.desktop

%post
alias_name="linuxtoys"
alias_command="/usr/bin/linuxtoys"
target_file="/etc/bash.bashrc"
if ! grep -q "alias $alias_name=" "$target_file"; then
    echo "alias $alias_name='$alias_command'" >> "$target_file"
    echo "Alias '$alias_name' created."
else
    echo "Alias '$alias_name' already exists."
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
/usr/bin/linuxtoys
/usr/bin/linuxtoys/*
/usr/share/icons/hicolor/scalable/apps/linuxtoys.png
/usr/share/applications/LinuxToys.desktop

%changelog
* Sat Aug 09 2025 Victor Gregory <psygreg@pm.me> - 4.3
- Reinstated distribution packaging
