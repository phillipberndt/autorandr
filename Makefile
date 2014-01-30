all:
	@echo "Call \"make install\" to install this program."
	@echo "Call \"make hotplug\" to install matching hotplug events."

INSTALL_PATH=/usr/local/bin
install:
	install -D auto-disper ${DESTDIR}${INSTALL_PATH}/auto-disper
	install -D -m 755 autorandr ${DESTDIR}${INSTALL_PATH}/autorandr
	install -D -m 644 bash_completion/autorandr ${DESTDIR}/etc/bash_completion.d/autorandr

hotplug:
	install -D -m 755 pm-utils/40autorandr ${DESTDIR}/etc/pm/sleep.d/40autorandr
	install -D -m 644 udev/40-monitor-hotplug.rules ${DESTDIR}/etc/udev/rules.d/40-monitor-hotplug.rules
ifeq (${USER},root)
	udevadm control --reload-rules
else
	@echo "Please run this command as root:"
	@echo "    udevadm control --reload-rules"
endif
