Name:           linuxtoys
Version:        1.6.2
Release:        1%{?dist}
Summary:        A set of tools for Linux presented in a user-friendly way
BuildArch:      x86_64

License:        GPL3
Source0:        linuxtoys-%{version}.tar.gz

Requires:       bash newt curl wget

%description
A menu with various handy tools for Linux gaming, optimization and other tweaks.

%prep
%setup -q

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/%{_bindir}
cp linuxtoys.sh $RPM_BUILD_ROOT/%{_bindir}
cp linuxtoys.png $RPM_BUILD_ROOT/%{_bindir}
cp LinuxToys.desktop $RPM_BUILD_ROOT/usr/share/applications

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{_bindir}/linuxtoys.sh
%{_bindir}/linuxtoys.png
/usr/share/applications/LinuxToys.desktop

%changelog
* Tue May  20 2025 Victor Gregory <psygreg@pm.me> - 1.6.2
- First version ported to .rpm package