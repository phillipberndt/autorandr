# autorandr 
Automatically select a display configuration based on connected devices

## Branch information

This is a compatible Python rewrite of
[wertarbyte/autorandr](https://github.com/wertarbyte/autorandr).

The original [wertarbyte/autorandr](https://github.com/wertarbyte/autorandr)
tree is unmaintained, with lots of open pull requests and issues. I forked it
and merged what I thought were the most important changes. If you are searching
for that version, see the [`legacy` branch](https://github.com/phillipberndt/autorandr/tree/legacy).
Note that the Python version is better suited for non-standard configurations,
like if you use `--transform` or `--reflect`. If you use `auto-disper`, you
have to use the bash version, as there is no disper support in the Python
version (yet). Both versions use a compatible configuration file format, so
you can, to some extent, switch between them.  I will maintain the `legacy`
branch until @wertarbyte finds the time to maintain his branch again.

If you are interested in why there are two versions around, see
[#7](https://github.com/phillipberndt/autorandr/issues/7),
[#8](https://github.com/phillipberndt/autorandr/issues/8) and
especially
[#12](https://github.com/phillipberndt/autorandr/issues/12)
if you are unhappy with this version and would like to contibute to the bash
version.

## License information and authors

autorandr is available under the terms of the GNU General Public License
(version 3).

Contributors to this version of autorandr are:

* Alexander Wirt
* Chris Dunder
* Daniel Hahler
* Maciej Sitarz
* Mathias Svensson
* Matthew R Johnson
* Nazar Mokrynskyi
* Phillip Berndt
* Rasmus Wriedt Larsen
* Stefan Tomanek
* Timo Bingmann
* Tomasz Bogdal
* Victor Häggqvist
* stormc
* tachylatus
* andersonjacob
* Simon Wydooghe

## Installation/removal
For Debian-based distributives (including Ubuntu) it is recommended to call `make deb` to obtain a package that can be installed and removed with `dpkg`.

On other distributives you can install autorandr by calling `make install` and remove it by calling `make uninstall`.

If you can contribute packaging script for other distributives, we will appreciate it.

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
`~/.config/autorandr` (or `~/.autorandr` if you have an old installation) as
well as in all profile directories: The scripts are executed after a mode
switch has taken place and can notify window managers or other applications
about it. The same holds for `preswitch`, which is executed before the switch
takes place, and `postsave`, which is executed after a profile was
stored/altered.

All scripts can also be placed in any of the `$XDG_CONFIG_DIRS`. In addition to
the script names themselves, any executables in subdirectories named
`script_name.d` (e.g. `postswitch.d`) are executed as well. In scripts, some of
autorandr's state is exposed as environment variables prefixed with `AUTORANDR_`.
The most useful one is `$AUTORANDR_CURRENT_PROFILE`.

## Apply configuration on login
With recent versions of autorandr you typically do not need to add autorandr to `~/.xprofile`, since an autostart configuration file will be installed at `/etc/xdg/autostart/autorandr.desktop` by the makefile. It will select an appropriate profile automatically.

If you need to customize this behaviour, you can always disable or modify it by placing an alternative desktop file with the same name in `~/.config/autostart` or by using a GUI configuration tool for autostart like `gnome-session-properties`.
