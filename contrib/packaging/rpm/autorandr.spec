%define name autorandr
%define version 1.11
%define release 1

# pmutils
%define use_pm_utils 1
%if 0%{?fedora} > 22
%define use_pm_utils 0
%endif
%if 0%{?rhel} > 7
%define use_pm_utils 0
%endif

# python 2 or 3
%define py_ver 3
%if 0%{?rhel}
%define py_ver 2
%endif

Summary: Automatically select a display configuration based on connected devices
Name: %{name}
Version: %{version}
Release: %{release}%{?dist}
Source0: https://github.com/phillipberndt/%{name}/archive/%{version}/%{name}-%{version}.tar.gz
License: GPLv3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Phillip Berndt <phillip.berndt@googlemail.com>
Url: https://github.com/phillipberndt/autorandr
Requires: python%{py_ver}
%if 0%{?use_pm_utils}
Requires:	pm-utils
%endif
%{?systemd_ordering}
BuildRequires: bash-completion
BuildRequires: python%{py_ver}-devel
BuildRequires: systemd
BuildRequires: udev
BuildRequires: gcc
BuildRequires: libxcb-devel
%if %{py_ver} == 2
BuildRequires: python3-devel
%endif


%description
Automatically select a display configuration based on connected devices

## Branch information

This is a compatible Python rewrite of
[wertarbyte/autorandr](https://github.com/wertarbyte/autorandr). Contributions
for bash-completion, fd.o/XDG autostart, Nitrogen, pm-utils, and systemd can be
found under [contrib](contrib/).

The original [wertarbyte/autorandr](https://github.com/wertarbyte/autorandr)
tree is unmaintained, with lots of open pull requests and issues. I forked it
and merged what I thought were the most important changes. If you are searching
for that version, see the [`legacy` branch](https://github.com/phillipberndt/autorandr/tree/legacy).
Note that the Python version is better suited for non-standard configurations,
like if you use `--transform` or `--reflect`. If you use `auto-disper`, you
have to use the bash version, as there is no disper support in the Python
version (yet). Both versions use a compatible configuration file format, so
you can, to some extent, switch between them.  I will maintain the `legacy`
branch until @wertarbyte finds the time to maintain his branch again.

If you are interested in why there are two versions around, see
[#7](https://github.com/phillipberndt/autorandr/issues/7),
[#8](https://github.com/phillipberndt/autorandr/issues/8) and
especially
[#12](https://github.com/phillipberndt/autorandr/issues/12)
if you are unhappy with this version and would like to contribute to the bash
version.


%package zsh-completion
Summary: zsh-completion for autorandr
Requires: zsh
Requires: %{name}
%description zsh-completion
This package provides zsh-completion files for autorandr

%package launcher
Summary: Launcher daemon for autorandr
Requires: libxcb
Requires: %{name}
%description launcher
This package provides launcher daemon for autorandr

%prep
%setup -n %{name}-%{version} -n %{name}-%{version}
%if %{py_ver} == 3
pathfix.py -pni "%{__python3} %{py3_shbang_opts}" ./autorandr.py
%else
pathfix.py -pni "%{__python2} %{py2_shbang_opts}" ./autorandr.py
%endif

%install
make DESTDIR="%{buildroot}" PREFIX=%{_prefix} install
make DESTDIR="%{buildroot}" PREFIX=%{_prefix} install_launcher
install -vDm 644 README.md -t "%{buildroot}/usr/share/doc/%{name}/"
install -vDm 644 contrib/zsh_completion/_autorandr -t %{buildroot}%{_datarootdir}/zsh/site-functions/


%files
%defattr(-,root,root,-)
%attr(0644,root,root) %{_unitdir}/autorandr.service
%license gpl-3.0.txt 
%doc README.md
%{_sysconfdir}/xdg/autostart/autorandr.desktop
%{_bindir}/autorandr
%{_mandir}
%{_datarootdir}/bash-completion/completions/autorandr
%{_udevrulesdir}/40-monitor-hotplug.rules

%files zsh-completion
%{_datarootdir}/zsh/site-functions/_autorandr

%files launcher
%{_bindir}/autorandr-launcher
%{_sysconfdir}/xdg/autostart/autorandr-launcher.desktop

%changelog
* Mon Jun 07 2021 Jerzy Drozdz <jerzy.drozdz@jdsieci.pl> - 1.11-1
- Updated to stable 1.11
- Added launcher subpackage
* Mon Jun 08 2020 Jerzy Drozdz <jerzy.drozdz@jdsieci.pl> - 1.10.1-1
- Updated to stable 1.10.1
- Added zsh-completion subpackage
* Wed May 22 2019 Maciej Sitarz <macieksitarz@wp.pl> - 1.8.1-1
- Updated to stable 1.8.1
* Fri Sep 28 2018 Maciej Sitarz <macieksitarz@wp.pl> - 1.7-1
- Updated to stable 1.7
* Thu Jul 19 2018 Maciej Sitarz <macieksitarz@wp.pl> - 1.5-1
- Updated to stable 1.5
- Changed dest path for systemd service file
* Sun Oct 01 2017 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 1.1-2
- Added conditionals for pm-utils, compability with Fedora26+
- Removed bash-completion from requisites
- Removed udev from requisites
* Sun Sep 03 2017 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 1.1-1
- Update to stable 1.1
* Fri Feb 17 2017 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 20170217git-1
- Update to master
* Wed Jul 6 2016 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 20160706git-1
- Set default value of $XDG_CONFIG_DIRS to fulfill the standard
* Fri Jul 1 2016 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 20160701git-1.1
- fixed running udevadm in post
* Fri Jul 1 2016 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 20160701git-1
- initial build
