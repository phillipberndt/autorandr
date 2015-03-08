#!/usr/bin/env python
# encoding: utf-8
#
# autorandr.py
# Copyright (c) 2015, Phillip Berndt
#
# Autorandr rewrite in Python
#
# This script aims to be fully compatible with the original autorandr.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function
import copy
import getopt

import binascii
import hashlib
import os
import re
import subprocess
import sys
from distutils.version import LooseVersion as Version

from itertools import chain
from collections import OrderedDict

virtual_profiles = [
    # (name, description, callback)
    ("common", "Clone all connected outputs at the largest common resolution", None),
    ("horizontal", "Stack all connected outputs horizontally at their largest resolution", None),
    ("vertical", "Stack all connected outputs vertically at their largest resolution", None),
]

help_text = """
Usage: autorandr [options]

-h, --help              get this small help
-c, --change            reload current setup
-s, --save <profile>    save your current setup to profile <profile>
-l, --load <profile>    load profile <profile>
-d, --default <profile> make profile <profile> the default profile
--force                 force (re)loading of a profile
--fingerprint           fingerprint your current hardware setup
--config                dump your current xrandr setup
--dry-run               don't change anything, only print the xrandr commands

 To prevent a profile from being loaded, place a script call "block" in its
 directory. The script is evaluated before the screen setup is inspected, and
 in case of it returning a value of 0 the profile is skipped. This can be used
 to query the status of a docking station you are about to leave.

 If no suitable profile can be identified, the current configuration is kept.
 To change this behaviour and switch to a fallback configuration, specify
 --default <profile>.

 Another script called "postswitch" can be placed in the directory
 ~/.config/autorandr (or ~/.autorandr if you have an old installation) as well
 as in any profile directories: The scripts are executed after a mode switch
 has taken place and can notify window managers.

 The following virtual configurations are available:
""".strip()

class XrandrOutput(object):
    "Represents an XRandR output"

    # This regular expression is used to parse an output in `xrandr --verbose'
    XRANDR_OUTPUT_REGEXP = """(?x)
        ^(?P<output>[^ ]+)\s+                                                           # Line starts with output name
        (?:                                                                             # Differentiate disconnected and connected in first line
            disconnected |
            unknown\ connection |
            (?P<connected>connected)\s+                                                 # If connected:
            (?:
            (?P<primary>primary\ )?                                                     # Might be primary screen
            (?P<width>[0-9]+)x(?P<height>[0-9]+)                                        # Resolution (might be overridden below!)
            \+(?P<x>[0-9]+)\+(?P<y>[0-9]+)\s+                                           # Position
            (?:\(0x[0-9a-fA-F]+\)\s+)?                                                  # XID
            (?P<rotate>(?:normal|left|right|inverted))\s+                               # Rotation
            (?:(?P<reflect>X\ and\ Y|X|Y)\ axis)?                                       # Reflection
            )?                                                                          # .. but everything of the above only if the screen is in use.
        ).*
        (?:\s*(?:                                                                       # Properties of the output
            Gamma: (?P<gamma>[0-9\.: ]+) |                                              # Gamma value
            Transform: (?P<transform>(?:[\-0-9\. ]+\s+){3}) |                           # Transformation matrix
            EDID: (?P<edid>\s*?(?:\\n\\t\\t[0-9a-f]+)+) |                               # EDID of the output
            (?![0-9])[^:\s][^:\n]+:.*(?:\s\\t[\\t ].+)*                                 # Other properties
        ))+
        \s*
        (?P<modes>(?:
            (?P<mode_width>[0-9]+)x(?P<mode_height>[0-9]+).+?\*current.+\s+
                h:.+\s+v:.+clock\s+(?P<rate>[0-9\.]+)Hz\s* |                            # Interesting (current) resolution: Extract rate
            [0-9]+x[0-9]+.+\s+h:.+\s+v:.+\s*                                            # Other resolutions
        )*)
    """

    XRANDR_OUTPUT_MODES_REGEXP = """(?x)
        (?P<width>[0-9]+)x(?P<height>[0-9]+)
        .*?(?P<preferred>\+preferred)?
        \s+h:.+
        \s+v:.+clock\s+(?P<rate>[0-9\.]+)Hz
    """

    XRANDR_13_DEFAULTS = {
        "transform": "1,0,0,0,1,0,0,0,1",
    }

    XRANDR_12_DEFAULTS = {
        "reflect": "normal",
        "rotate": "normal",
        "gamma": "1.0:1.0:1.0",
    }

    XRANDR_DEFAULTS = dict(list(XRANDR_13_DEFAULTS.items()) + list(XRANDR_12_DEFAULTS.items()))

    def __repr__(self):
        return "<%s%s %s>" % (self.output, (" %s..%s" % (self.edid[:5], self.edid[-5:])) if self.edid else "", " ".join(self.option_vector))

    @property
    def options_with_defaults(self):
        "Return the options dictionary, augmented with the default values that weren't set"
        if "off" in self.options:
            return self.options
        options = {}
        if xrandr_version() >= Version("1.3"):
            options.update(self.XRANDR_13_DEFAULTS)
        if xrandr_version() >= Version("1.2"):
            options.update(self.XRANDR_12_DEFAULTS)
        options.update(self.options)
        return options

    @property
    def option_vector(self):
        "Return the command line parameters for XRandR for this instance"
        return sum([["--%s" % option[0], option[1]] if option[1] else ["--%s" % option[0]] for option in chain((("output", self.output),), sorted(self.options_with_defaults.items()))], [])

    @property
    def option_string(self):
        "Return the command line parameters in the configuration file format"
        return "\n".join([ " ".join(option) if option[1] else option[0] for option in chain((("output", self.output),), sorted(self.options.items()))])

    @property
    def sort_key(self):
        "Return a key to sort the outputs for xrandr invocation"
        if not self.edid:
            return -1
        if "pos" in self.options:
            x, y = map(float, self.options["pos"].split("x"))
        else:
            x, y = 0, 0
        return x + 10000 * y

    def __init__(self, output, edid, options):
        "Instanciate using output name, edid and a dictionary of XRandR command line parameters"
        self.output = output
        self.edid = edid
        self.options = options
        self.remove_default_option_values()

    def remove_default_option_values(self):
        "Remove values from the options dictionary that are superflous"
        if "off" in self.options and len(self.options.keys()) > 1:
            self.options = { "off": None }
            return
        for option, default_value in self.XRANDR_DEFAULTS.items():
            if option in self.options and self.options[option] == default_value:
                del self.options[option]

    @classmethod
    def from_xrandr_output(cls, xrandr_output):
        """Instanciate an XrandrOutput from the output of `xrandr --verbose'

        This method also returns a list of modes supported by the output.
        """
        try:
            xrandr_output = xrandr_output.replace("\r\n", "\n")
            match_object = re.search(XrandrOutput.XRANDR_OUTPUT_REGEXP, xrandr_output)
        except:
            raise RuntimeError("Parsing XRandR output failed, there is an error in the regular expression.")
        if not match_object:
            debug = debug_regexp(XrandrOutput.XRANDR_OUTPUT_REGEXP, xrandr_output)
            raise RuntimeError("Parsing XRandR output failed, the regular expression did not match: %s" % debug)
        remainder = xrandr_output[len(match_object.group(0)):]
        if remainder:
            raise RuntimeError(("Parsing XRandR output failed, %d bytes left unmatched after regular expression, "
                                "starting at byte %d with ..'%s'.") % (len(remainder), len(len(match_object.group(0))), remainder[:10]))

        match = match_object.groupdict()

        modes = []
        if match["modes"]:
            modes = [ x.groupdict() for x in re.finditer(XrandrOutput.XRANDR_OUTPUT_MODES_REGEXP, match["modes"]) ]
            if not modes:
                raise RuntimeError("Parsing XRandR output failed, couldn't find any display modes")

        options = {}
        if not match["connected"]:
            options["off"] = None
            edid = None
        elif not match["width"]:
            options["off"] = None
            edid = "".join(match["edid"].strip().split())
        else:
            if match["mode_width"]:
                options["mode"] = "%sx%s" % (match["mode_width"], match["mode_height"])
            else:
                if match["rotate"] not in ("left", "right"):
                    options["mode"] = "%sx%s" % (match["width"], match["height"])
                else:
                    options["mode"] = "%sx%s" % (match["height"], match["width"])
            options["rotate"] = match["rotate"]
            if match["primary"]:
                options["primary"] = None
            if match["reflect"] == "X":
                options["reflect"] = "x"
            elif match["reflect"] == "Y":
                options["reflect"] = "y"
            elif match["reflect"] == "X and Y":
                options["reflect"] = "xy"
            options["pos"] = "%sx%s" % (match["x"], match["y"])
            if match["transform"]:
                transformation = ",".join(match["transform"].strip().split())
                if transformation != "1.000000,0.000000,0.000000,0.000000,1.000000,0.000000,0.000000,0.000000,1.000000":
                    options["transform"] = transformation
                    if not match["mode_width"]:
                        # TODO We'd need to apply the reverse transformation here. Let's see if someone complains, I doubt that this
                        # special case is actually required.
                        print("Warning: Output %s has a transformation applied. Could not determine correct mode!", file=sys.stderr)
            if match["gamma"]:
                gamma = match["gamma"].strip()
                options["gamma"] = gamma
            if match["rate"]:
                options["rate"] = match["rate"]
            edid = "".join(match["edid"].strip().split())

        return XrandrOutput(match["output"], edid, options), modes

    @classmethod
    def from_config_file(cls, edid_map, configuration):
        "Instanciate an XrandrOutput from the contents of a configuration file"
        options = {}
        for line in configuration.split("\n"):
            if line:
                line = line.split(None, 1)
                options[line[0]] = line[1] if len(line) > 1 else None

        edid = None

        if options["output"] in edid_map:
            edid = edid_map[options["output"]]
        else:
            # This fuzzy matching is for legacy autorandr that used sysfs output names
            fuzzy_edid_map = [ re.sub("(card[0-9]+|-)", "", x) for x in edid_map.keys() ]
            fuzzy_output = re.sub("(card[0-9]+|-)", "", options["output"])
            if fuzzy_output in fuzzy_edid_map:
                edid = edid_map[list(edid_map.keys())[fuzzy_edid_map.index(fuzzy_output)]]
            elif "off" not in options:
                raise RuntimeError("Failed to find an EDID for output `%s' in setup file, required as `%s' is not off in config file."
                                   % (options["output"], options["output"]))
        output = options["output"]
        del options["output"]

        return XrandrOutput(output, edid, options)

    def edid_equals(self, other):
        "Compare to another XrandrOutput's edid and on/off-state, taking legacy autorandr behaviour (md5sum'ing) into account"
        if self.edid and other.edid:
            if len(self.edid) == 32 and len(other.edid) != 32:
                return hashlib.md5(binascii.unhexlify(other.edid)).hexdigest() == self.edid
            if len(self.edid) != 32 and len(other.edid) == 32:
                return hashlib.md5(binascii.unhexlify(self.edid)).hexdigest() == other.edid
        return self.edid == other.edid

    def __eq__(self, other):
        return self.edid_equals(other) and self.output == other.output and self.options == other.options

def xrandr_version():
    "Return the version of XRandR that this system uses"
    if getattr(xrandr_version, "version", False) is False:
        version_string = os.popen("xrandr -v").read()
        try:
            version = re.search("xrandr program version\s+([0-9\.]+)", version_string).group(1)
            xrandr_version.version = Version(version)
        except AttributeError:
            xrandr_version.version = Version("1.3.0")

    return xrandr_version.version

def debug_regexp(pattern, string):
    "Use the partial matching functionality of the regex module to display debug info on a non-matching regular expression"
    try:
        import regex
        bounds = ( 0, len(string) )
        while bounds[0] != bounds[1]:
            half = int((bounds[0] + bounds[1]) / 2)
            if half == bounds[0]:
                break
            bounds = (half, bounds[1]) if regex.search(pattern, string[:half], partial=True) else (bounds[0], half - 1)
        partial_length = bounds[0]
        return ("Regular expression matched until position "
              "%d, ..'%s', and did not match from '%s'.." % (partial_length, string[max(0, partial_length-20):partial_length],
                                                             string[partial_length:partial_length+10]))
    except ImportError:
        pass
    return "Debug information available if `regex' module is installed."

def parse_xrandr_output():
    "Parse the output of `xrandr --verbose' into a list of outputs"
    xrandr_output = os.popen("xrandr -q --verbose").read()
    if not xrandr_output:
        raise RuntimeError("Failed to run xrandr")

    # We are not interested in screens
    xrandr_output = re.sub("(?m)^Screen [0-9].+", "", xrandr_output).strip()

    # Split at output boundaries and instanciate an XrandrOutput per output
    split_xrandr_output = re.split("(?m)^([^ ]+ (?:(?:dis)?connected|unknown connection).*)$", xrandr_output)
    if len(split_xrandr_output) < 2:
        raise RuntimeError("No output boundaries found")
    outputs = OrderedDict()
    modes = OrderedDict()
    for i in range(1, len(split_xrandr_output), 2):
        output_name = split_xrandr_output[i].split()[0]
        output, output_modes = XrandrOutput.from_xrandr_output("".join(split_xrandr_output[i:i+2]))
        outputs[output_name] = output
        if output_modes:
            modes[output_name] = output_modes

    return outputs, modes

def load_profiles(profile_path):
    "Load the stored profiles"

    profiles = {}
    for profile in os.listdir(profile_path):
        config_name = os.path.join(profile_path, profile, "config")
        setup_name  = os.path.join(profile_path, profile, "setup")
        if not os.path.isfile(config_name) or not os.path.isfile(setup_name):
            continue

        edids = dict([ x.strip().split() for x in open(setup_name).readlines() if x.strip() ])

        config = {}
        buffer = []
        for line in chain(open(config_name).readlines(), ["output"]):
            if line[:6] == "output" and buffer:
                config[buffer[0].strip().split()[-1]] = XrandrOutput.from_config_file(edids, "".join(buffer))
                buffer = [ line ]
            else:
                buffer.append(line)

        for output_name in list(config.keys()):
            if config[output_name].edid is None:
                del config[output_name]

        profiles[profile] = { "config": config, "path": os.path.join(profile_path, profile), "config-mtime": os.stat(config_name).st_mtime }

    return profiles

def find_profiles(current_config, profiles):
    "Find profiles matching the currently connected outputs"
    detected_profiles = []
    for profile_name, profile in profiles.items():
        config = profile["config"]
        matches = True
        for name, output in config.items():
            if not output.edid:
                continue
            if name not in current_config or not output.edid_equals(current_config[name]):
                matches = False
                break
        if not matches or any(( name not in config.keys() for name in current_config.keys() if current_config[name].edid )):
            continue
        if matches:
            detected_profiles.append(profile_name)
    return detected_profiles

def profile_blocked(profile_path):
    "Check if a profile is blocked"
    script = os.path.join(profile_path, "blocked")
    if not os.access(script, os.X_OK | os.F_OK):
        return False
    return subprocess.call(script) == 0

def output_configuration(configuration, config):
    "Write a configuration file"
    outputs = sorted(configuration.keys(), key=lambda x: configuration[x].sort_key)
    for output in outputs:
        print(configuration[output].option_string, file=config)

def output_setup(configuration, setup):
    "Write a setup (fingerprint) file"
    outputs = sorted(configuration.keys())
    for output in outputs:
        if configuration[output].edid:
            print(output, configuration[output].edid, file=setup)

def save_configuration(profile_path, configuration):
    "Save a configuration into a profile"
    if not os.path.isdir(profile_path):
        os.makedirs(profile_path)
    with open(os.path.join(profile_path, "config"), "w") as config:
        output_configuration(configuration, config)
    with open(os.path.join(profile_path, "setup"), "w") as setup:
        output_setup(configuration, setup)

def update_mtime(filename):
    "Update a file's mtime"
    try:
        os.utime(filename, None)
        return True
    except:
        return False

def apply_configuration(configuration, dry_run=False):
    "Apply a configuration"
    outputs = sorted(configuration.keys(), key=lambda x: configuration[x].sort_key)
    if dry_run:
        base_argv = [ "echo", "xrandr" ]
    else:
        base_argv = [ "xrandr" ]

    # There are several xrandr / driver bugs we need to take care of here:
    # - We cannot enable more than two screens at the same time
    #   See https://github.com/phillipberndt/autorandr/pull/6
    #   and commits f4cce4d and 8429886.
    # - We cannot disable all screens
    #   See https://github.com/phillipberndt/autorandr/pull/20
    # - We should disable screens before enabling others, because there's
    #   a limit on the number of enabled screens
    # - We must make sure that the screen at 0x0 is activated first,
    #   or the other (first) screen to be activated would be moved there.

    disable_outputs = []
    enable_outputs = []
    for output in outputs:
        if not configuration[output].edid or "off" in configuration[output].options:
            disable_outputs.append(configuration[output].option_vector)
        else:
            enable_outputs.append(configuration[output].option_vector)

    # Disable all but the last of the outputs to be disabled
    if len(disable_outputs) > 1:
        if subprocess.call(base_argv + list(chain.from_iterable(disable_outputs[:-1]))) != 0:
            # Disabling the outputs failed. Retry with the next command:
            # Sometimes disabling of outputs fails due to an invalid RRSetScreenSize.
            # This does not occur if simultaneously the primary screen is reset.
            pass
        else:
            disable_outputs = disable_outputs[-1:]

    # If disable_outputs still has more than one output in it, one of the xrandr-calls below would
    # disable the last two screens. This is a problem, so if this would happen, instead disable only
    # one screen in the first call below.
    if len(disable_outputs) > 0 and len(disable_outputs) % 2 == 0:
        # In the context of a xrandr call that changes the display state, `--query' should do nothing
        disable_outputs.insert(0, ['--query'])

    # Enable the remaining outputs in pairs of two operations
    operations = disable_outputs + enable_outputs
    for index in range(0, len(operations), 2):
        argv = base_argv + list(chain.from_iterable(operations[index:index+2]))
        if subprocess.call(argv) != 0:
            raise RuntimeError("Command failed: %s" % " ".join(argv))

def add_unused_outputs(source_configuration, target_configuration):
    "Add outputs that are missing in target to target, in 'off' state"
    for output_name, output in source_configuration.items():
        if output_name not in target_configuration:
            target_configuration[output_name] = XrandrOutput(output_name, output.edid, { "off": None })

def remove_irrelevant_outputs(source_configuration, target_configuration):
    "Remove outputs from target that ought to be 'off' and already are"
    for output_name, output in source_configuration.items():
        if "off" in output.options and output_name in target_configuration and "off" in target_configuration[output_name].options:
            del target_configuration[output_name]

def generate_virtual_profile(configuration, modes, profile_name):
    "Generate one of the virtual profiles"
    configuration = copy.deepcopy(configuration)
    if profile_name == "common":
        common_resolution = [ set(( ( mode["width"], mode["height"] ) for mode in output )) for output in modes.values() ]
        common_resolution = reduce(lambda a, b: a & b, common_resolution[1:], common_resolution[0])
        common_resolution = sorted(common_resolution, key=lambda a: int(a[0])*int(a[1]))
        if common_resolution:
            for output in configuration:
                configuration[output].options = {}
                if output in modes:
                    configuration[output].options["mode"] = "%sx%s" % common_resolution[-1]
                    configuration[output].options["pos"] = "0x0"
                else:
                    configuration[output].options["off"] = None
    elif profile_name in ("horizontal", "vertical"):
        shift = 0
        if profile_name == "horizontal":
            shift_index = "width"
            pos_specifier = "%sx0"
        else:
            shift_index = "height"
            pos_specifier = "0x%s"

        for output in configuration:
            configuration[output].options = {}
            if output in modes:
                mode = sorted(modes[output], key=lambda a: int(a["width"])*int(a["height"]) + (10**6 if a["preferred"] else 0))[-1]
                configuration[output].options["mode"] = "%sx%s" % (mode["width"], mode["height"])
                configuration[output].options["rate"] = mode["rate"]
                configuration[output].options["pos"] = pos_specifier % shift
                shift += int(mode[shift_index])
            else:
                configuration[output].options["off"] = None
    return configuration

def exit_help():
    "Print help and exit"
    print(help_text)
    for profile in virtual_profiles:
        print("  %-10s %s" % profile[:2])
    sys.exit(0)

def exec_scripts(profile_path, script_name):
    "Run userscripts"
    for script in (os.path.join(profile_path, script_name), os.path.join(os.path.dirname(profile_path), script_name)):
        if os.access(script, os.X_OK | os.F_OK):
            subprocess.call(script)

def main(argv):
    try:
       options = dict(getopt.getopt(argv[1:], "s:l:d:cfh", [ "dry-run", "change", "default=", "save=", "load=", "force", "fingerprint", "config", "help" ])[0])
    except getopt.GetoptError as e:
        print(str(e))
        options = { "--help": True }

    profiles = {}
    try:
        # Load profiles from each XDG config directory
        for directory in os.environ.get("XDG_CONFIG_DIRS", "").split(":"):
            system_profile_path = os.path.join(directory, "autorandr")
            if os.path.isdir(system_profile_path):
                profiles.update(load_profiles(system_profile_path))
        # For the user's profiles, prefer the legacy ~/.autorandr if it already exists
        # profile_path is also used later on to store configurations
        profile_path = os.path.expanduser("~/.autorandr")
        if not os.path.isdir(profile_path):
            # Elsewise, follow the XDG specification
            profile_path = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "autorandr")
        if os.path.isdir(profile_path):
            profiles.update(load_profiles(profile_path))
        # Sort by descending mtime
        profiles = OrderedDict(sorted(profiles.items(), key=lambda x: -x[1]["config-mtime"]))
    except Exception as e:
        print("Failed to load profiles:\n%s" % str(e), file=sys.stderr)
        sys.exit(1)

    try:
        config, modes = parse_xrandr_output()
    except Exception as e:
        print("Failed to parse current configuration from XRandR:\n%s" % str(e), file=sys.stderr)
        sys.exit(1)

    if "--fingerprint" in options:
        output_setup(config, sys.stdout)
        sys.exit(0)

    if "--config" in options:
        output_configuration(config, sys.stdout)
        sys.exit(0)

    if "-s" in options:
        options["--save"] = options["-s"]
    if "--save" in options:
        if options["--save"] in ( x[0] for x in virtual_profiles ):
            print("Cannot save current configuration as profile '%s':\nThis configuration name is a reserved virtual configuration." % options["--save"])
            sys.exit(1)
        try:
            save_configuration(os.path.join(profile_path, options["--save"]), config)
        except Exception as e:
            print("Failed to save current configuration as profile '%s':\n%s" % (options["--save"], str(e)), file=sys.stderr)
            sys.exit(1)
        print("Saved current configuration as profile '%s'" % options["--save"])
        sys.exit(0)

    if "-h" in options or "--help" in options:
        exit_help()

    detected_profiles = find_profiles(config, profiles)
    load_profile = False

    if "-l" in options:
        options["--load"] = options["-l"]
    if "--load" in options:
        load_profile = options["--load"]
    else:
        for profile_name in profiles.keys():
            if profile_blocked(os.path.join(profile_path, profile_name)):
                print("%s (blocked)" % profile_name, file=sys.stderr)
                continue
            if profile_name in detected_profiles:
                print("%s (detected)" % profile_name, file=sys.stderr)
                if ("-c" in options or "--change" in options) and not load_profile:
                    load_profile = profile_name
            else:
                print(profile_name, file=sys.stderr)

    if "-d" in options:
        options["--default"] = options["-d"]
    if not load_profile and "--default" in options:
        load_profile = options["--default"]

    if load_profile:
        if load_profile in ( x[0] for x in virtual_profiles ):
            load_config = generate_virtual_profile(config, modes, load_profile)
            scripts_path = os.path.join(profile_path, load_profile)
        else:
            try:
                profile = profiles[load_profile]
                load_config = profile["config"]
                scripts_path = profile["path"]
            except KeyError:
                print("Failed to load profile '%s':\nProfile not found" % load_profile, file=sys.stderr)
                sys.exit(1)
            if load_profile in detected_profiles and detected_profiles[0] != load_profile:
                update_mtime(os.path.join(scripts_path, "config"))
        add_unused_outputs(config, load_config)
        if load_config == dict(config) and not "-f" in options and not "--force" in options:
            print("Config already loaded", file=sys.stderr)
            sys.exit(0)
        remove_irrelevant_outputs(config, load_config)

        try:
            if "--dry-run" in options:
                apply_configuration(load_config, True)
            else:
                exec_scripts(scripts_path, "preswitch")
                apply_configuration(load_config, False)
                exec_scripts(scripts_path, "postswitch")
        except Exception as e:
            print("Failed to apply profile '%s':\n%s" % (load_profile, str(e)), file=sys.stderr)
            sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        print("General failure. Please report this as a bug:\n%s" % (str(e),), file=sys.stderr)
        sys.exit(1)
