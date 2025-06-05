Name:           linuxtoys
Version:        2.1.4
Release:        1
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.xz

Requires:       bash newt curl wget alacritty git
BuildRequires:  desktop-file-utils

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/linuxtoys
install -m 755 opt/linuxtoys/linuxtoys.sh %{buildroot}/opt/linuxtoys
install -m 644 opt/linuxtoys/linuxtoys.png %{buildroot}/opt/linuxtoys
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
/opt/linuxtoys/linuxtoys.sh
/opt/linuxtoys/linuxtoys.png
/usr/share/applications/LinuxToys.desktop

%changelog
* Thu Jun  5 2025 Victor Gregory <psygreg@pm.me> - 2.1.4
- bugfix: now updater works as intended
