Name:           linuxtoys
Version:        3.0
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash newt curl wget git
# BuildRequires:  desktop-file-utils

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%global debug_package %{nil}

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps
install -m 755 usr/bin/linuxtoys.sh %{buildroot}/usr/bin
install -m 644 usr/share/icons/hicolor/scalable/apps/linuxtoys.png %{buildroot}/usr/share/icons/hicolor/scalable/apps
mkdir -p %{buildroot}/usr/share/applications
desktop-file-install --dir=%{buildroot}/usr/share/applications usr/share/applications/LinuxToys.desktop

%post
alias_name="linuxtoys"
alias_command="/usr/bin/linuxtoys.sh"
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
/usr/bin/linuxtoys.sh
/usr/share/icons/hicolor/scalable/apps/linuxtoys.png
/usr/share/applications/LinuxToys.desktop

%changelog
* Thu Jun  5 2025 Victor Gregory <psygreg@pm.me> - 3.0
- added Console Mode
- bugfix internet detection (GitHub #10)
