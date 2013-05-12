# autorandr

Automatically select a display configuration based on connected devices

Stefan Tomanek <[stefan.tomanek@wertarbyte.de](stefan.tomanek@wertarbyte.de)>

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
