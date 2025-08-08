Name:           linuxtoys
Version:        4.2
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash zenity curl wget git
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
install -m 755 linuxtoys.sh %{buildroot}/usr/bin
install -m 755 linuxtoys.lib %{buildroot}/usr/bin/linuxtoys
install -m 755 en %{buildroot}/usr/bin/linuxtoys
install -m 755 pt %{buildroot}/usr/bin/linuxtoys
install -m 644 linuxtoys.png %{buildroot}/usr/share/icons/hicolor/scalable/apps
mkdir -p %{buildroot}/usr/share/applications
desktop-file-install --dir=%{buildroot}/usr/share/applications LinuxToys.desktop

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
/usr/bin/linuxtoys/linuxtoys.lib
/usr/bin/linuxtoys/en
/usr/bin/linuxtoys/pt
/usr/share/icons/hicolor/scalable/apps/linuxtoys.png
/usr/share/applications/LinuxToys.desktop

%changelog
* Fri Aug 8 2025 Victor Gregory <psygreg@pm.me> - 4.2
- Reinstated distribution packaging
