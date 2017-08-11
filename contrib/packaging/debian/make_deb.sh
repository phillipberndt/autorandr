#!/bin/sh
#

# Determine version
if git rev-parse --git-dir >/dev/null 2>&1; then
	V="$(git describe --tags 2>/dev/null)"
	if [ "$?" -ne 0 ]; then
		V=0.1
	fi
else
	V=0.1
fi

# Create/determine working directory
P="`dirname $(readlink -f "$0")`"
LD="autorandr-$V"
D="$P/$LD"
O="`pwd`/$LD.deb"

if [ -d "$D" ]; then
	echo "Directory $D does already exist. Aborting.."
	exit 1
fi

# Error handling: On error, abort and clear $D
_cleanup() {
	rm -rf "$D"
}
trap _cleanup EXIT
set -e

mkdir $D

# Debian(ish) specific part
make -C "$P/../../../" \
	DESTDIR="$D" \
	TARGETS="autorandr bash_completion autostart_config systemd udev" \
	BASH_COMPLETION_DIR=/usr/share/bash-completion/completions \
	SYSTEMD_UNIT_DIR=/lib/systemd/system \
	PM_UTILS_DIR=/usr/lib/pm-utils/sleep.d \
	UDEV_RULES_DIR=/lib/udev/rules.d/ \
	install

SIZE=$(du -s $D | awk '{print $1}')

cp -r "$P/debian" "$D/DEBIAN"
chmod 0755 "$D/DEBIAN"
[ -d "$D/etc" ] && (cd $D; find etc -type f) > "$D/DEBIAN/conffiles"
sed -i -re "s#Version:.+#Version: $V#" "$D/DEBIAN/control"
echo "Installed-Size: $SIZE" >> "$D/DEBIAN/control"
fakeroot dpkg-deb -b "$D" "$O"
