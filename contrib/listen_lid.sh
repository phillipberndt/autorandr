#!/bin/sh
#
# /!\ You must be part of the input group
# sudo gpasswd -a $USER input

stdbuf -oL libinput debug-events | \
    grep -E --line-buffered '^[[:space:]-]+event[0-9]+[[:space:]]+SWITCH_TOGGLE[[:space:]]' | \
    while read line; do
    autorandr --change --default default
done
