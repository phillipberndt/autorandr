#!/bin/sh
#
# /!\ You must be part of the input group
# sudo gpasswd -a $USER input

stdbuf -oL libinput debug-events | \
    egrep --line-buffered '^[\s-]+event[0-9]+\s+SWITCH_TOGGLE\s' | \
    while read line; do
    autorandr --change --default default
done
