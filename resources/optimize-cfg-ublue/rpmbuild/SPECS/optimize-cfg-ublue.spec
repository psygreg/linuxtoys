Name:           optimize-cfg-ublue
Version:        1.0
Release:        1
Summary:        LinuxToys systemd optimizer patches for Universal Blue systems.
BuildArch:      x86_64

License:        GPL3
Source0:        optimize-cfg-ublue-%{version}.tar.xz

Requires:       bash

%description
CachyOS configs ported to atomic Fedora.

%global debug_package %{nil}

%prep
%setup -q

%install
mkdir -p %{buildroot}/usr/lib/udev/rules.d/
mkdir -p %{buildroot}/usr/lib/tmpfiles.d/
mkdir -p %{buildroot}/usr/lib/modprobe.d/
mkdir -p %{buildroot}/usr/lib/sysctl.d/
mkdir -p %{buildroot}/usr/lib/systemd/journald.conf.d/
mkdir -p %{buildroot}/etc/sysctl.d/
install -m 755 20-audio-pm.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 40-hpet-permissions.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 50-sata.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 60-ioschedulers.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 69-hdparm.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 99-cpu-dma-latency.rules %{buildroot}/usr/lib/udev/rules.d
install -m 755 thp.conf %{buildroot}/usr/lib/tmpfiles.d
install -m 755 thp-shrinker.conf %{buildroot}/usr/lib/tmpfiles.d
install -m 755 amdgpu.conf %{buildroot}/usr/lib/modprobe.d
install -m 755 nvidia.conf %{buildroot}/usr/lib/modprobe.d
install -m 755 blacklist.conf %{buildroot}/usr/lib/modprobe.d
install -m 755 99-cachyos-settings.conf %{buildroot}/usr/lib/sysctl.d
install -m 755 00-journal-size.conf %{buildroot}/usr/lib/systemd/journald.conf.d
install -m 755 99-splitlock.conf %{buildroot}/etc/sysctl.d

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-, root, root, -)
/usr/lib/sysctl.d/99-cachyos-settings.conf
/usr/lib/systemd/journald.conf.d/00-journal-size.conf
/usr/lib/modprobe.d/amdgpu.conf
/usr/lib/modprobe.d/blacklist.conf
/usr/lib/modprobe.d/nvidia.conf
/usr/lib/tmpfiles.d/thp.conf
/usr/lib/tmpfiles.d/thp-shrinker.conf
/usr/lib/udev/rules.d/20-audio-pm.rules
/usr/lib/udev/rules.d/40-hpet-permissions.rules
/usr/lib/udev/rules.d/50-sata.rules
/usr/lib/udev/rules.d/60-ioschedulers.rules
/usr/lib/udev/rules.d/69-hdparm.rules
/usr/lib/udev/rules.d/99-cpu-dma-latency.rules
/etc/sysctl.d/99-splitlock.conf

%changelog
* Tue Sep  23 2025 Victor Gregory <psygreg@pm.me> - 1.0
- Created separate package for Universal Blue
