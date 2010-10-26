#!/usr/bin/awk
/^[^ ]+ (dis)?connected / {
	DEV=$1;
	ID[DEV] = "";
}

$1 ~ /^[a-f0-9]+$/ {
	ID[DEV] = ID[DEV] $1
}

END {
	for (X in ID) {
		print X " " ID[X];
	}
}
