#!/bin/bash
#
# /!\ You must be part of the input group
# sudo gpasswd -a $USER input

libinput debug-events | grep SWITCH_TOGGLE | while read event; do
    autorandr --change --default default
done
