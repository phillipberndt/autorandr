Name:           autorandr
Version:        1.1
Release:        1%{?dist}
Summary:        Automatically select a display configuration based on connected devices

License:        GPL
URL:            https://github.com/phillipberndt/autorandr
Source0:        https://github.com/phillipberndt/%{name}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:	noarch
Requires:       systemd udev bash-completion pm-utils

%description


%prep
%setup -q

%build

%install

install -D -m 755 autorandr.py %{buildroot}%{_bindir}/autorandr
install -D -m 644 contrib/bash_completion/autorandr %{buildroot}%{_sysconfdir}/bash_completion.d/autorandr
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

#%post
#udevadm control --reload-rules


%changelog
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
