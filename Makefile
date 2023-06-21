DESTDIR=/
PREFIX=/usr/
RPM_SPEC=contrib/packaging/rpm/autorandr.spec
CFLAGS?=-O2 -Wall
CLEANUP_FILES=

.PHONY: all install uninstall autorandr bash_completion autostart_config pmutils systemd udev

all:
	@echo "Call \"make install\" to install this program."
	@echo "Call \"make uninstall\" to remove this program."
	@echo
	@echo "The following components were autodetected and will be installed:"
	@echo " "$(DEFAULT_TARGETS)
	@echo
	@echo "The following locations have been detected (from pkg-config):"
	@echo " - BASH_COMPLETIONS_DIR: $(BASH_COMPLETIONS_DIR)"
	@echo " - SYSTEMD_UNIT_DIR: $(SYSTEMD_UNIT_DIR)"
	@echo " - UDEV_RULES_DIR: $(UDEV_RULES_DIR)"
	@echo " - PM_SLEEPHOOKS_DIR: $(PM_SLEEPHOOKS_DIR)"
	@echo
	@echo "You can use the TARGETS variable to override this, but need to set"
	@echo "the SYSTEMD_UNIT_DIR, PM_SLEEPHOOKS_DIR and UDEV_RULES_DIR variables"
	@echo "in case they were not detected correctly."
	@echo
	@echo 'E.g. "make install TARGETS='autorandr pmutils' PM_UTILS_DIR=/etc/pm/sleep.d".'
	@echo
	@echo "An additional TARGETS variable \"launcher\" is available. This"
	@echo "installs a launcher called \"autorandr_launcher\". The launcher"
	@echo "is able to be run by the user and calls autorandr automatically"
	@echo "without using udev rules. The launcher is an alternative to the"
	@echo "udev/systemd setup that is more stable for some users."
	@echo
	@echo "The following additional targets are available:"
	@echo
	@echo "    make deb        creates a Debian package"
	@echo "    make rpm        creates a RPM package"

# Rules for autorandr itself
DEFAULT_TARGETS=autorandr

install_autorandr:
	mkdir -p ${DESTDIR}${PREFIX}/bin
	install -m 755 autorandr.py ${DESTDIR}${PREFIX}/bin/autorandr

uninstall_autorandr:
	rm -f ${DESTDIR}${PREFIX}/bin/autorandr

# Rules for bash-completion
BASH_COMPLETIONS_DIR:=$(shell pkg-config --variable=completionsdir bash-completion 2>/dev/null)
ifneq (,$(BASH_COMPLETIONS_DIR))
DEFAULT_TARGETS+=bash_completion
endif

install_bash_completion:
	mkdir -p ${DESTDIR}/${BASH_COMPLETIONS_DIR}
	install -m 644 contrib/bash_completion/autorandr ${DESTDIR}/${BASH_COMPLETIONS_DIR}/autorandr

uninstall_bash_completion:
	rm -f ${DESTDIR}/${BASH_COMPLETIONS_DIR}/autorandr

# Rules for autostart config
XDG_AUTOSTART_DIR=/etc/xdg/autostart
DEFAULT_TARGETS+=autostart_config

install_autostart_config:
	mkdir -p ${DESTDIR}/${XDG_AUTOSTART_DIR}
	install -m 644 contrib/etc/xdg/autostart/autorandr.desktop ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop
	# KDE-specific autostart (workaround for https://github.com/systemd/systemd/issues/18791)
	install -m 644 contrib/etc/xdg/autostart/autorandr.desktop ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-kde.desktop
	desktop-file-edit --remove-key=X-GNOME-Autostart-Phase --add-only-show-in=KDE ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-kde.desktop

ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-kde.desktop
endif

uninstall_autostart_config:
	rm -f ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop
	rm -f ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-kde.desktop

# Rules for systemd
SYSTEMD_UNIT_DIR:=$(shell pkg-config --variable=systemdsystemunitdir systemd 2>/dev/null)
ifneq (,$(SYSTEMD_UNIT_DIR))
DEFAULT_TARGETS+=systemd
endif

install_systemd:
	$(if $(SYSTEMD_UNIT_DIR),,$(error SYSTEMD_UNIT_DIR is not defined))
	mkdir -p ${DESTDIR}/${SYSTEMD_UNIT_DIR}
	install -m 644 contrib/systemd/autorandr.service ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service
	install -m 644 contrib/systemd/autorandr-lid-listener.service ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr-lid-listener.service
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service
endif
	@echo
	@echo "To activate the systemd units, run this command as root:"
	@echo "    systemctl daemon-reload"
	@echo "    systemctl enable autorandr.service"
	@echo "    systemctl enable autorandr-lid-listener.service"
	@echo

uninstall_systemd:
	$(if $(SYSTEMD_UNIT_DIR),,$(error SYSTEMD_UNIT_DIR is not defined))
	rm -f ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service
	rm -f ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr-lid-listener.service

# Rules for pmutils
PM_SLEEPHOOKS_DIR:=$(shell pkg-config --variable=pm_sleephooks pm-utils 2>/dev/null)
ifneq (,$(PM_SLEEPHOOKS_DIR))
ifeq (,$(SYSTEMD_UNIT_DIR))
DEFAULT_TARGETS+=pmutils
endif
endif

install_pmutils:
	$(if $(PM_SLEEPHOOKS_DIR),,$(error PM_SLEEPHOOKS_DIR is not defined))
	mkdir -p ${DESTDIR}/${PM_SLEEPHOOKS_DIR}
	install -m 755 contrib/pm-utils/40autorandr ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr
endif

uninstall_pmutils:
	$(if $(PM_SLEEPHOOKS_DIR),,$(error PM_SLEEPHOOKS_DIR is not defined))
	rm -f ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr


# Rules for udev
UDEV_RULES_DIR:=$(shell pkg-config --variable=udevdir udev 2>/dev/null)/rules.d
ifneq (/rules.d,$(UDEV_RULES_DIR))
DEFAULT_TARGETS+=udev
endif

install_udev:
	$(if $(UDEV_RULES_DIR),,$(error UDEV_RULES_DIR is not defined))
	mkdir -p ${DESTDIR}/${UDEV_RULES_DIR}/
	echo 'ACTION=="change", SUBSYSTEM=="drm", RUN+="$(if $(findstring systemd, $(DEFAULT_TARGETS)),/bin/systemctl start --no-block autorandr.service,${PREFIX}/bin/autorandr --batch --change --default default)"' > ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules
	@echo
	@echo "To activate the udev rules, run this command as root:"
	@echo "    udevadm control --reload-rules"
	@echo

uninstall_udev:
	$(if $(UDEV_RULES_DIR),,$(error UDEV_RULES_DIR is not defined))
	rm -f ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules

# Rules for manpage
MANDIR:=${PREFIX}/share/man/man1
DEFAULT_TARGETS+=manpage

install_manpage:
	mkdir -p ${DESTDIR}/${MANDIR}
	cp autorandr.1 ${DESTDIR}/${MANDIR}

uninstall_manpage:
	rm -f ${DESTDIR}/${MANDIR}/autorandr.1

# Rules for launcher
LAUNCHER_LDLIBS=$(shell pkg-config --libs pkg-config xcb xcb-randr 2>/dev/null)
ifneq (,$(LAUNCHER_LDLIBS))
CLEANUP_FILES+=contrib/autorandr_launcher/autorandr-launcher
LAUNCHER_CFLAGS=$(shell pkg-config --cflags pkg-config xcb xcb-randr 2>/dev/null)
contrib/autorandr_launcher/autorandr-launcher: contrib/autorandr_launcher/autorandr_launcher.c
	$(CC) $(CFLAGS) $(LAUNCHER_CFLAGS) -o $@ $+ $(LDFLAGS) $(LAUNCHER_LDLIBS) $(LDLIBS)

install_launcher: contrib/autorandr_launcher/autorandr-launcher
	mkdir -p ${DESTDIR}${PREFIX}/bin
	install -m 755 contrib/autorandr_launcher/autorandr-launcher ${DESTDIR}${PREFIX}/bin/autorandr-launcher
	mkdir -p ${DESTDIR}/${XDG_AUTOSTART_DIR}
	install -m 644 contrib/etc/xdg/autostart/autorandr-launcher.desktop ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-launcher.desktop
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr-launcher#$(subst #,\#,${PREFIX})/bin/autorandr-launcher#g' ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-launcher.desktop
endif
endif

uninstall_launcher:
	rm -f ${DESTDIR}${PREFIX}/bin/autorandr-launcher
	rm -f ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr-launcher.desktop

TARGETS=$(DEFAULT_TARGETS)
install: $(patsubst %,install_%,$(TARGETS))
uninstall: $(patsubst %,uninstall_%,$(TARGETS))

deb:
	./contrib/packaging/debian/make_deb.sh

rpm:
	spectool -g -R $(RPM_SPEC)
	rpmbuild -ba $(RPM_SPEC)

clean:
	rm -f $(CLEANUP_FILES)
