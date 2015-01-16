# autorandr

Automatically select a display configuration based on connected devices

## Branch information

The original [wertarbyte/autorandr](https://github.com/wertarbyte/autorandr)
tree is unmaintained, with lots of open pull requests and issues. I forked
it and merged what I thought were the most important changes. I will maintain
this branch until @wertarbyte finds the time to maintain his branch again.

## License information and authors

autorandr is available under the terms of the GNU General Public License
(version 3).

Contributors to this version of autorandr are:

* Alexander Wirt
* Chris Dunder
* Maciej Sitarz
* Matthew R Johnson
* Phillip Berndt
* Stefan Tomanek
* Timo Bingmann
* Tomasz Bogdal
* stormc
* tachylatus

## How to use

Save your current display configuration and setup with:
```
autorandr --save mobile
```

Connect an additional display, configure your setup and save it:
```
autorandr --save docked
```

Now autorandr can detect which hardware setup is active:
```
 $ autorandr
   mobile
   docked (detected)
```

To automatically reload your setup, just append `--change` to the command line

To manually load a profile, you can use the `--load <profile>` option.

autorandr tries to avoid reloading an identical configuration. To force the
(re)configuration, apply `--force`.

To prevent a profile from being loaded, place a script call _block_ in its
directory. The script is evaluated before the screen setup is inspected, and
in case of it returning a value of 0 the profile is skipped. This can be used
to query the status of a docking station you are about to leave.

If no suitable profile can be identified, the current configuration is kept.
To change this behaviour and switch to a fallback configuration, specify
`--default <profile>`.

Another script called `postswitch` can be placed in the directory
`~/.autorandr` as well as in all profile directories: The scripts are executed
after a mode switch has taken place and can notify window managers or other
applications about it.

While the script uses xrandr by default, calling it by the name `autodisper`
or `auto-disper` forces it to use the [disper](http://willem.engen.nl/projects/disper/)
utility, which is useful for controlling nvidia chipsets. The formats for
fingerprinting the current setup and saving/loading the current configuration
are adjusted accordingly.

To install autorandr call `make install`, define your setup and then call
`make hotplug` to install hotplug scripts.

For Debian using auto-disper:
To make the screen auto-configure when your computer wakes up,
* Copy auto-disper into /usr/local/bin/
* Copy pm-utils/40auto-disper into /etc/pm/sleep.d/
* (Assuming gnome) Run gnome-keybinding-properties and ADD a shortcut,
  I called it "Run auto-disper", I set it to CTRL-F7, and the command is:
  `auto-disper -c --default default`
* Create a default disper setting... eg for laptop: unplug all monitors,
  set up the screen nicely on the laptop display.
  Then run `auto-disper --save laptop`
