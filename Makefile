DESTDIR=/
PREFIX=/usr/

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
	@echo "The following additional targets are available:"
	@echo
	@echo "    make deb        creates a Debian package"

# Rules for autorandr itself
DEFAULT_TARGETS=autorandr

install_autorandr:
	install -D -m 755 autorandr.py ${DESTDIR}${PREFIX}/bin/autorandr

uninstall_autorandr:
	rm -f ${DESTDIR}${PREFIX}/bin/autorandr

# Rules for bash-completion
BASH_COMPLETIONS_DIR:=$(shell pkg-config --variable=completionsdir bash-completion 2>/dev/null)
ifneq (,$(BASH_COMPLETIONS_DIR))
DEFAULT_TARGETS+=bash_completion
endif

install_bash_completion:
	install -D -m 644 contrib/bash_completion/autorandr ${DESTDIR}/${BASH_COMPLETIONS_DIR}/autorandr

uninstall_bash_completion:
	rm -f ${DESTDIR}/${BASH_COMPLETIONS_DIR}/autorandr

# Rules for autostart config
XDG_AUTOSTART_DIR=/etc/xdg/autostart
DEFAULT_TARGETS+=autostart_config

install_autostart_config:
	install -D -m 644 contrib/etc/xdg/autostart/autorandr.desktop ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop
endif

uninstall_autostart_config:
	rm -f ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop

# Rules for systemd
SYSTEMD_UNIT_DIR:=$(shell pkg-config --variable=systemdsystemunitdir systemd 2>/dev/null)
ifneq (,$(SYSTEMD_UNIT_DIR))
DEFAULT_TARGETS+=systemd
endif

install_systemd:
	$(if $(SYSTEMD_UNIT_DIR),,$(error SYSTEMD_UNIT_DIR is not defined))
	install -D -m 644 contrib/systemd/autorandr.service ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service
endif
	@echo
	@echo "To activate the systemd unit, run this command as root:"
	@echo "    systemctl daemon-reload"
	@echo "    systemctl enable autorandr.service"
	@echo

uninstall_systemd:
	$(if $(SYSTEMD_UNIT_DIR),,$(error SYSTEMD_UNIT_DIR is not defined))
	rm -f ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr.service

# Rules for pmutils
PM_SLEEPHOOKS_DIR:=$(shell pkg-config --variable=pm_sleephooks pm-utils 2>/dev/null)
ifneq (,$(PM_SLEEPHOOKS_DIR))
ifeq (,$(SYSTEMD_UNIT_DIR))
DEFAULT_TARGETS+=pmutils
endif
endif

install_pmutils:
	$(if $(PM_SLEEPHOOKS_DIR),,$(error PM_SLEEPHOOKS_DIR is not defined))
	install -D -m 755 contrib/pm-utils/40autorandr ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr
ifneq ($(PREFIX),/usr/)
	sed -i -re 's#/usr/bin/autorandr#$(subst #,\#,${PREFIX})/bin/autorandr#g' ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr
endif

uninstall_pmutils:
	$(if $(PM_SLEEPHOOKS_DIR),,$(error PM_SLEEPHOOKS_DIR is not defined))
	rm -f ${DESTDIR}/${PM_SLEEPHOOKS_DIR}/40autorandr


# Rules for udev
UDEV_RULES_DIR:=$(shell pkg-config --variable=udevdir udev 2>/dev/null)/rules.d
ifneq (,$(UDEV_RULES_DIR),y)
DEFAULT_TARGETS+=udev
endif

install_udev:
	$(if $(UDEV_RULES_DIR),,$(error UDEV_RULES_DIR is not defined))
	mkdir -p ${DESTDIR}/${UDEV_RULES_DIR}/
	echo 'ACTION=="change", SUBSYSTEM=="drm", RUN+="$(if $(findstring systemd, $(TARGETS)),/bin/systemctl start --no-block autorandr.service,${PREFIX}/bin/autorandr --batch --change --default default)"' > ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules
	@echo
	@echo "To activate the udev rules, run this command as root:"
	@echo "    udevadm control --reload-rules"
	@echo

uninstall_udev:
	$(if $(UDEV_RULES_DIR),,$(error UDEV_RULES_DIR is not defined))
	rm -f ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules


TARGETS=$(DEFAULT_TARGETS)
install: $(patsubst %,install_%,$(TARGETS))
uninstall: $(patsubst %,uninstall_%,$(TARGETS))

deb:
	./contrib/packaging/debian/make_deb.sh
