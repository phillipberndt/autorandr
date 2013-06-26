
install:
	install -m 774 autorandr          /usr/bin/
	install -m 774 autorandr_monitor  /usr/bin/
	install -m 644 bash_completion/autorandr /etc/bash_completion.d/
	ln -sf /usr/bin/autorandr /usr/bin/auto-disper
	#install -m pm-utils/40autorandr /etc/pm/power.d/
