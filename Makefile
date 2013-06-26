
install:
	install        auto-disper        /usr/bin/
	install -m 774 autorandr          /usr/bin/
	install -m 774 autorandr_monitor  /usr/bin/
	install -m 644 bash_completion/autorandr /etc/bash_completion.d/
	#install -m pm-utils/40autorandr /etc/pm/power.d/
