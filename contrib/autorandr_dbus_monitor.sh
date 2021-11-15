#!/bin/bash
# Copyright 2021 Christophe-Marie Duquesne

pipe=$(mktemp -u /tmp/autorandr.XXXXXXXX)

trap "rm -f $pipe" EXIT

if [[ ! -p $pipe ]]; then
    mkfifo $pipe
fi

suspend_event="type='signal',interface='org.freedesktop.login1.Manager',member='PrepareForSleep'"
lid_event="type='signal',path=/org/freedesktop/UPower,member=PropertiesChanged"
display_event="type='signal',path=/org/freedesktop/ColorManager"

stdbuf -oL dbus-monitor --system --profile $lid_event | grep "LidIsClosed" > $pipe &
stdbuf -oL dbus-monitor --system --profile $display_event > $pipe &
stdbuf -oL dbus-monitor --system --profile $suspend_event > $pipe &

while true; do
    if read line <$pipe; then
        autorandr --change --default default
    fi
done

echo "Exiting"
