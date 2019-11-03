#!/bin/bash
#
# /!\ You must be part of the input group
# sudo gpasswd -a $USER input

stdbuf -oL libinput debug-events | grep --line-buffered SWITCH_TOGGLE | while read line; do
    autorandr --change --default default
done
