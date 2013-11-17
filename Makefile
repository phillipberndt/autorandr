all:
	@echo "Call \"make install\" to install this program."
	@echo "Call \"make hotplug\" to install matching hotplug events."

INSTALL_PATH=/usr/local/bin
install:
	install auto-disper ${INSTALL_PATH}
	install -m 755 autorandr ${INSTALL_PATH}
	install -m 644 bash_completion/autorandr /etc/bash_completion.d/

hotplug:
	install -m 755 pm-utils/40autorandr /etc/pm/power.d/