DESTDIR=/
PREFIX=/usr/

.PHONY: all install uninstall autorandr bash_completion pmutils systemd udev

all:
	@echo "Call \"make install\" to install this program."
	@echo "Call \"make uninstall\" to remove this program."
	@echo
	@echo "The following components were autodetected and will be installed:"
	@echo " "$(DEFAULT_TARGETS)
	@echo "You can use the TARGETS variable to override, e.g. \"make install TAGETS='autorandr pmutils'\"."

# Rules for autorandr itself
DEFAULT_TARGETS=autorandr

install_autorandr:
	install -D -m 755 autorandr.py ${DESTDIR}${PREFIX}/bin/autorandr

uninstall_autorandr:
	rm -f ${DESTDIR}${PREFIX}/bin/autorandr

# Rules for bash_completion
HAVE_BASH_COMPLETION=$(shell [ -d /etc/bash_completion.d/ ] && echo "y")
ifeq ($(HAVE_BASH_COMPLETION),y)
DEFAULT_TARGETS+=bash_completion
endif

install_bash_completion:
	install -D -m 644 contrib/bash_completion/autorandr ${DESTDIR}/etc/bash_completion.d/autorandr

uninstall_bash_completion:
	rm -f ${DESTDIR}/etc/bash_completion.d/autorandr

# Rules for pmutils
HAVE_PMUTILS=$(shell [ -x /usr/sbin/pm-suspend ] && echo "y")
ifeq ($(HAVE_PMUTILS),y)
DEFAULT_TARGETS+=pmutils
endif

install_pmutils:
	install -D -m 755 contrib/pm-utils/40autorandr ${DESTDIR}/etc/pm/sleep.d/40autorandr

uninstall_pmutils:
	rm -f ${DESTDIR}/etc/pm/sleep.d/40autorandr

# Rules for systemd
HAVE_SYSTEMD=$(shell grep -q systemd /proc/1/comm && echo "y")
ifeq ($(HAVE_SYSTEMD),y)
DEFAULT_TARGETS+=systemd
endif

install_systemd:
	install -D -m 644 contrib/systemd/autorandr-resume.service ${DESTDIR}/etc/systemd/system/autorandr-resume.service

uninstall_systemd:
	rm -f ${DESTDIR}/etc/systemd/system/autorandr-resume.service

# Rules for udev
HAVE_UDEV=$(shell [ -d /etc/udev/rules.d/ ] && echo "y")
ifeq ($(HAVE_UDEV),y)
DEFAULT_TARGETS+=udev
endif

install_udev:
	install -D -m 644 contrib/udev/40-monitor-hotplug.rules ${DESTDIR}/etc/udev/rules.d/40-monitor-hotplug.rules
ifeq (${USER},root)
	udevadm control --reload-rules
else
	@echo "Please run this command as root:"
	@echo "    udevadm control --reload-rules"
endif

uninstall_udev:
	rm -f ${DESTDIR}/etc/udev/rules.d/40-monitor-hotplug.rules
	
HAVE_NITROGEN=$(shell type nitrogen &>/dev/null && echo "y")
ifeq ($(HAVE_NITROGEN),y)
DEFAULT_TARGETS+=nitrogen
endif

# Rules for nitrogen
NITROGEN=autorandr_nitrogen_wallpaper
install_nitrogen:
	install -D -m 755 contrib/${NITROGEN}/${NITROGEN} ${DESTDIR}${PREFIX}/bin/${NITROGEN}

uninstall_nitrogen:
	rm -f ${DESTDIR}${PREFIX}/bin/${NITROGEN}


TARGETS=$(DEFAULT_TARGETS)
install: $(patsubst %,install_%,$(TARGETS))
uninstall: $(patsubst %,uninstall_%,$(TARGETS))
