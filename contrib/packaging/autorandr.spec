%define use_pm_utils 1
%if 0%{?fedora} > 22
%define use_pm_utils 0
%endif
%if 0%{?rhel} > 7
%define use_pm_utils 0
%endif

Name:           autorandr
Version:        1.1
Release:        2%{?dist}
Summary:        Automatically select a display configuration based on connected devices

License:        GPL
URL:            https://github.com/phillipberndt/autorandr
Source0:        https://github.com/phillipberndt/%{name}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch
Requires:       systemd
%if 0%{?use_pm_utils}
Requires:	pm-utils
%endif

%description


%prep
%setup -q

%build

%install

install -D -m 755 autorandr.py %{buildroot}%{_bindir}/autorandr
install -D -m 644 contrib/bash_completion/autorandr %{buildroot}%{_datarootdir}/autorandr/completions/autorandr
install -d -m 755 %{buildroot}%{_datarootdir}/bash-completion/completions
ln -s ../../autorandr/completions/autorandr %{buildroot}%{_datarootdir}/bash-completion/completions/autorandr
install -D -m 755 contrib/pm-utils/40autorandr %{buildroot}%{_sysconfdir}/pm/sleep.d/40autorandr
install -D -m 644 contrib/systemd/autorandr.service %{buildroot}%{_sysconfdir}/systemd/system/autorandr.service
#install -D -m 644 contrib/udev/40-monitor-hotplug.rules %{buildroot}%{_sysconfdir}/udev/rules.d/40-monitor-hotplug.rules
install -D -m 644 contrib/etc/xdg/autostart/autorandr.desktop %{buildroot}%{_sysconfdir}/etc/xdg/autostart/autorandr.desktop

%files
%defattr(-,root,root,-)

%license gpl-3.0.txt 
%doc README.md
%{_bindir}/*
%config(noreplace) %{_sysconfdir}/*
%{_datarootdir}/autorandr/*
%{_datarootdir}/bash-completion/completions/autorandr

#%post
#udevadm control --reload-rules


%changelog
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
