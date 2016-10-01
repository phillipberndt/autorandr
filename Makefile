DESTDIR=/
PREFIX=/usr/

.PHONY: all install uninstall autorandr bash_completion autostart_config pmutils systemd udev

all:
	@echo "Call \"make install\" to install this program."
	@echo "Call \"make uninstall\" to remove this program."
	@echo
	@echo "The following components were autodetected and will be installed:"
	@echo " "$(DEFAULT_TARGETS)
	@echo "You can use the TARGETS variable to override, e.g. \"make install TAGETS='autorandr pmutils'\"."
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

# Rules for bash_completion
BASH_COMPLETION_DIR=/etc/bash_completion.d
HAVE_BASH_COMPLETION=$(shell [ -d /etc/bash_completion.d/ ] && echo "y")
ifeq ($(HAVE_BASH_COMPLETION),y)
DEFAULT_TARGETS+=bash_completion
endif

install_bash_completion:
	install -D -m 644 contrib/bash_completion/autorandr ${DESTDIR}/${BASH_COMPLETION_DIR}/autorandr

uninstall_bash_completion:
	rm -f ${DESTDIR}/${BASH_COMPLETION_DIR}/autorandr

# Rules for autostart config
XDG_AUTOSTART_DIR=/etc/xdg/autostart

install_autostart_config:
	install -D -m 644 contrib/etc/xdg/autostart/autorandr.desktop ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop

uninstall_autostart_config:
	rm -f ${DESTDIR}/${XDG_AUTOSTART_DIR}/autorandr.desktop

# Rules for pmutils
PM_UTILS_DIR=/etc/pm/sleep.d
HAVE_PMUTILS=$(shell [ -x /usr/sbin/pm-suspend ] && echo "y")
ifeq ($(HAVE_PMUTILS),y)
DEFAULT_TARGETS+=pmutils
endif

install_pmutils:
	install -D -m 755 contrib/pm-utils/40autorandr ${DESTDIR}/${PM_UTILS_DIR}/40autorandr

uninstall_pmutils:
	rm -f ${DESTDIR}/${PM_UTILS_DIR}/40autorandr

# Rules for systemd
SYSTEMD_UNIT_DIR=/etc/systemd/system/
HAVE_SYSTEMD=$(shell grep -q systemd /proc/1/comm && echo "y")
ifeq ($(HAVE_SYSTEMD),y)
DEFAULT_TARGETS+=systemd
endif

install_systemd:
	install -D -m 644 contrib/systemd/autorandr-resume.service ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr-resume.service

uninstall_systemd:
	rm -f ${DESTDIR}/${SYSTEMD_UNIT_DIR}/autorandr-resume.service

# Rules for udev
UDEV_RULES_DIR=/etc/udev/rules.d
HAVE_UDEV=$(shell [ -d "${UDEV_RULES_DIR}" ] && echo "y")
ifeq ($(HAVE_UDEV),y)
DEFAULT_TARGETS+=udev
endif

install_udev:
	install -D -m 644 contrib/udev/40-monitor-hotplug.rules ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules
ifeq (${USER},root)
	udevadm control --reload-rules
else
	@echo "Please run this command as root:"
	@echo "    udevadm control --reload-rules"
endif

uninstall_udev:
	rm -f ${DESTDIR}/${UDEV_RULES_DIR}/40-monitor-hotplug.rules


TARGETS=$(DEFAULT_TARGETS)
install: $(patsubst %,install_%,$(TARGETS))
uninstall: $(patsubst %,uninstall_%,$(TARGETS))

deb:
	./contrib/packaging/debian/make_deb.sh
