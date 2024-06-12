Name:           autorandr
Version:        1.15
Release:        %autorelease
Summary:        Automatically select a display configuration based on connected devices

BuildArch:      noarch
BuildRequires:  python3-devel

License:        GPLv3
URL:            https://github.com/phillipberndt/%{name}
Source0:        %{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildRequires: make
BuildRequires: systemd
BuildRequires: udev
BuildRequires: desktop-file-utils

Recommends:    (%{name}-bash-completion = %{version}-%{release} if bash)
Recommends:    (%{name}-fish-completion = %{version}-%{release} if fish)
Recommends:    (%{name}-zsh-completion = %{version}-%{release} if zsh)

%description
%{summary}.

%prep
%setup -q
%py3_shebang_fix ./autorandr.py

%post
udevadm control --reload-rules
%systemd_post autorandr.service

%preun
%systemd_preun autorandr.service

%postun
%systemd_postun autorandr.service

%package bash-completion
Summary: Bash completion for autorandr
Requires: %{name}
Requires: bash-completion
%description bash-completion
This package provides bash-completion files for autorandr

%package fish-completion
Summary: Fish completion for autorandr
Requires: %{name}
Requires: fish-completion
%description fish-completion
This package provides fish-completion files for autorandr

%package zsh-completion
Summary: Zsh completion for autorandr
Requires: zsh
Requires: %{name}
%description zsh-completion
This package provides zsh-completion files for autorandr

%install
%make_install
install -vDm 644 README.md -t "%{buildroot}/usr/share/doc/%{name}/"
install -vDm 644 contrib/bash_completion/autorandr -t %{buildroot}%{_datadir}/bash-completion/completions/
install -vDm 644 contrib/fish_completion/autorandr.fish -t %{buildroot}%{_datadir}/fish/vendor_completions.d/
install -vDm 644 contrib/zsh_completion/_autorandr -t %{buildroot}%{_datadir}/zsh/site-functions/
install -vDm 644 autorandr.1 -t %{buildroot}%{_mandir}/man1/

%check
desktop-file-validate %{buildroot}%{_sysconfdir}/xdg/autostart/autorandr.desktop

%files
%license gpl-3.0.txt
%doc README.md
%{_mandir}/man1/*
%{_bindir}/autorandr
%{_unitdir}/autorandr.service
%{_unitdir}/autorandr-lid-listener.service
%{_sysconfdir}/xdg/autostart/autorandr.desktop
%{_sysconfdir}/xdg/autostart/autorandr-kde.desktop
%{_udevrulesdir}/40-monitor-hotplug.rules

%files bash-completion
%{_datadir}/bash-completion/completions/autorandr

%files fish-completion
%{_datadir}/fish/vendor_completions.d/autorandr.fish

%files zsh-completion
%{_datadir}/zsh/site-functions/_autorandr

%changelog
%autochangelog
