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

import binascii
import copy
import fnmatch
import getopt
import hashlib
import os
import posix
import pwd
import re
import subprocess
import sys
import shutil
import time

from collections import OrderedDict
from distutils.version import LooseVersion as Version
from functools import reduce
from itertools import chain

if sys.version_info.major == 2:
    import ConfigParser as configparser
else:
    import configparser

__version__ = "1.7"

try:
    input = raw_input
except NameError:
    pass

virtual_profiles = [
    # (name, description, callback)
    ("off", "Disable all outputs", None),
    ("common", "Clone all connected outputs at the largest common resolution", None),
    ("clone-largest", "Clone all connected outputs with the largest resolution (scaled down if necessary)", None),
    ("horizontal", "Stack all connected outputs horizontally at their largest resolution", None),
    ("vertical", "Stack all connected outputs vertically at their largest resolution", None),
]

help_text = """
Usage: autorandr [options]

-h, --help              get this small help
-c, --change            automatically load the first detected profile
-d, --default <profile> make profile <profile> the default profile
-l, --load <profile>    load profile <profile>
-s, --save <profile>    save your current setup to profile <profile>
-r, --remove <profile>  remove profile <profile>
--batch                 run autorandr for all users with active X11 sessions
--current               only list current (active) configuration(s)
--config                dump your current xrandr setup
--debug                 enable verbose output
--detected              only list detected (available) configuration(s)
--dry-run               don't change anything, only print the xrandr commands
--fingerprint           fingerprint your current hardware setup
--force                 force (re)loading of a profile
--skip-options <option> comma separated list of xrandr arguments (e.g. "gamma")
                        to skip both in detecting changes and applying a profile
--version               show version information and exit

 If no suitable profile can be identified, the current configuration is kept.
 To change this behaviour and switch to a fallback configuration, specify
 --default <profile>.

 autorandr supports a set of per-profile and global hooks. See the documentation
 for details.

 The following virtual configurations are available:
""".strip()


class AutorandrException(Exception):
    def __init__(self, message, original_exception=None, report_bug=False):
        self.message = message
        self.report_bug = report_bug
        if original_exception:
            self.original_exception = original_exception
            trace = sys.exc_info()[2]
            while trace.tb_next:
                trace = trace.tb_next
            self.line = trace.tb_lineno
            self.file_name = trace.tb_frame.f_code.co_filename
        else:
            try:
                import inspect
                frame = inspect.currentframe().f_back
                self.line = frame.f_lineno
                self.file_name = frame.f_code.co_filename
            except:
                self.line = None
                self.file_name = None
            self.original_exception = None

        if os.path.abspath(self.file_name) == os.path.abspath(sys.argv[0]):
            self.file_name = None

    def __str__(self):
        retval = [self.message]
        if self.line:
            retval.append(" (line %d%s)" % (self.line, ("; %s" % self.file_name) if self.file_name else ""))
        if self.original_exception:
            retval.append(":\n  ")
            retval.append(str(self.original_exception).replace("\n", "\n  "))
        if self.report_bug:
            retval.append("\nThis appears to be a bug. Please help improving autorandr by reporting it upstream:"
                          "\nhttps://github.com/phillipberndt/autorandr/issues"
                          "\nPlease attach the output of `xrandr --verbose` to your bug report if appropriate.")
        return "".join(retval)


class XrandrOutput(object):
    "Represents an XRandR output"

    # This regular expression is used to parse an output in `xrandr --verbose'
    XRANDR_OUTPUT_REGEXP = """(?x)
        ^(?P<output>[^ ]+)\s+                                                           # Line starts with output name
        (?:                                                                             # Differentiate disconnected and connected
            disconnected |                                                              # in first line
            unknown\ connection |
            (?P<connected>connected)
        )
        \s*
        (?P<primary>primary\ )?                                                         # Might be primary screen
        (?:\s*
            (?P<width>[0-9]+)x(?P<height>[0-9]+)                                        # Resolution (might be overridden below!)
            \+(?P<x>-?[0-9]+)\+(?P<y>-?[0-9]+)\s+                                       # Position
            (?:\(0x[0-9a-fA-F]+\)\s+)?                                                  # XID
            (?P<rotate>(?:normal|left|right|inverted))\s+                               # Rotation
            (?:(?P<reflect>X\ and\ Y|X|Y)\ axis)?                                       # Reflection
        )?                                                                              # .. but only if the screen is in use.
        (?:[\ \t]*\([^\)]+\))(?:\s*[0-9]+mm\sx\s[0-9]+mm)?
        (?:[\ \t]*panning\ (?P<panning>[0-9]+x[0-9]+\+[0-9]+\+[0-9]+))?                 # Panning information
        (?:[\ \t]*tracking\ (?P<tracking>[0-9]+x[0-9]+\+[0-9]+\+[0-9]+))?               # Tracking information
        (?:[\ \t]*border\ (?P<border>(?:[0-9]+/){3}[0-9]+))?                            # Border information
        (?:\s*(?:                                                                       # Properties of the output
            Gamma: (?P<gamma>(?:inf|[0-9\.: e])+) |                                     # Gamma value
            Transform: (?P<transform>(?:[\-0-9\. ]+\s+){3}) |                           # Transformation matrix
            EDID: (?P<edid>\s*?(?:\\n\\t\\t[0-9a-f]+)+) |                               # EDID of the output
            (?![0-9])[^:\s][^:\n]+:.*(?:\s\\t[\\t ].+)*                                 # Other properties
        ))+
        \s*
        (?P<modes>(?:
            (?P<mode_name>\S+).+?\*current.*\s+                                         # Interesting (current) resolution:
             h:\s+width\s+(?P<mode_width>[0-9]+).+\s+                                   # Extract rate
             v:\s+height\s+(?P<mode_height>[0-9]+).+clock\s+(?P<rate>[0-9\.]+)Hz\s* |
            \S+(?:(?!\*current).)+\s+h:.+\s+v:.+\s*                                     # Other resolutions
        )*)
    """

    XRANDR_OUTPUT_MODES_REGEXP = """(?x)
        (?P<name>\S+).+?(?P<preferred>\+preferred)?\s+
         h:\s+width\s+(?P<width>[0-9]+).+\s+
         v:\s+height\s+(?P<height>[0-9]+).+clock\s+(?P<rate>[0-9\.]+)Hz\s* |
    """

    XRANDR_13_DEFAULTS = {
        "transform": "1,0,0,0,1,0,0,0,1",
        "panning": "0x0",
    }

    XRANDR_12_DEFAULTS = {
        "reflect": "normal",
        "rotate": "normal",
        "gamma": "1.0:1.0:1.0",
    }

    XRANDR_DEFAULTS = dict(list(XRANDR_13_DEFAULTS.items()) + list(XRANDR_12_DEFAULTS.items()))

    EDID_UNAVAILABLE = "--CONNECTED-BUT-EDID-UNAVAILABLE-"

    def __repr__(self):
        return "<%s%s %s>" % (self.output, self.short_edid, " ".join(self.option_vector))

    @property
    def short_edid(self):
        return ("%s..%s" % (self.edid[:5], self.edid[-5:])) if self.edid else ""

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
        return {a: b for a, b in options.items() if a not in self.ignored_options}

    @property
    def filtered_options(self):
        "Return a dictionary of options without ignored options"
        return {a: b for a, b in self.options.items() if a not in self.ignored_options}

    @property
    def option_vector(self):
        "Return the command line parameters for XRandR for this instance"
        args = ["--output", self.output]
        for option, arg in sorted(self.options_with_defaults.items()):
            args.append("--%s" % option)
            if arg:
                args.append(arg)
        return args

    @property
    def option_string(self):
        "Return the command line parameters in the configuration file format"
        options = ["output %s" % self.output]
        for option, arg in sorted(self.filtered_options.items()):
            if arg:
                options.append("%s %s" % (option, arg))
            else:
                options.append(option)
        return "\n".join(options)

    @property
    def sort_key(self):
        "Return a key to sort the outputs for xrandr invocation"
        if not self.edid:
            return -2
        if "off" in self.options:
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
        self.ignored_options = []
        self.remove_default_option_values()

    def set_ignored_options(self, options):
        "Set a list of xrandr options that are never used (neither when comparing configurations nor when applying them)"
        self.ignored_options = list(options)

    def remove_default_option_values(self):
        "Remove values from the options dictionary that are superflous"
        if "off" in self.options and len(self.options.keys()) > 1:
            self.options = {"off": None}
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
            raise AutorandrException("Parsing XRandR output failed, there is an error in the regular expression.",
                                     report_bug=True)
        if not match_object:
            debug = debug_regexp(XrandrOutput.XRANDR_OUTPUT_REGEXP, xrandr_output)
            raise AutorandrException("Parsing XRandR output failed, the regular expression did not match: %s" % debug,
                                     report_bug=True)
        remainder = xrandr_output[len(match_object.group(0)):]
        if remainder:
            raise AutorandrException("Parsing XRandR output failed, %d bytes left unmatched after "
                                     "regular expression, starting at byte %d with ..'%s'." %
                                     (len(remainder), len(match_object.group(0)), remainder[:10]),
                                     report_bug=True)

        match = match_object.groupdict()

        modes = []
        if match["modes"]:
            modes = []
            for mode_match in re.finditer(XrandrOutput.XRANDR_OUTPUT_MODES_REGEXP, match["modes"]):
                if mode_match.group("name"):
                    modes.append(mode_match.groupdict())
            if not modes:
                raise AutorandrException("Parsing XRandR output failed, couldn't find any display modes", report_bug=True)

        options = {}
        if not match["connected"]:
            edid = None
        elif match["edid"]:
            edid = "".join(match["edid"].strip().split())
        else:
            edid = "%s-%s" % (XrandrOutput.EDID_UNAVAILABLE, match["output"])

        if not match["width"]:
            options["off"] = None
        else:
            if match["mode_name"]:
                options["mode"] = match["mode_name"]
            elif match["mode_width"]:
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
            if match["panning"]:
                panning = [match["panning"]]
                if match["tracking"]:
                    panning += ["/", match["tracking"]]
                    if match["border"]:
                        panning += ["/", match["border"]]
                options["panning"] = "".join(panning)
            if match["transform"]:
                transformation = ",".join(match["transform"].strip().split())
                if transformation != "1.000000,0.000000,0.000000,0.000000,1.000000,0.000000,0.000000,0.000000,1.000000":
                    options["transform"] = transformation
                    if not match["mode_name"]:
                        # TODO We'd need to apply the reverse transformation here. Let's see if someone complains,
                        # I doubt that this special case is actually required.
                        print("Warning: Output %s has a transformation applied. Could not determine correct mode! "
                              "Using `%s'." % (match["output"], options["mode"]), file=sys.stderr)
            if match["gamma"]:
                gamma = match["gamma"].strip()
                # xrandr prints different values in --verbose than it accepts as a parameter value for --gamma
                # Also, it is not able to work with non-standard gamma ramps. Finally, it auto-corrects 0 to 1,
                # so we approximate by 1e-10.
                gamma = ":".join([str(max(1e-10, round(1. / float(x), 3))) for x in gamma.split(":")])
                options["gamma"] = gamma
            if match["rate"]:
                options["rate"] = match["rate"]

        return XrandrOutput(match["output"], edid, options), modes

    @classmethod
    def from_config_file(cls, edid_map, configuration):
        "Instanciate an XrandrOutput from the contents of a configuration file"
        options = {}
        for line in configuration.split("\n"):
            if line:
                line = line.split(None, 1)
                if line and line[0].startswith("#"):
                    continue
                options[line[0]] = line[1] if len(line) > 1 else None

        edid = None

        if options["output"] in edid_map:
            edid = edid_map[options["output"]]
        else:
            # This fuzzy matching is for legacy autorandr that used sysfs output names
            fuzzy_edid_map = [re.sub("(card[0-9]+|-)", "", x) for x in edid_map.keys()]
            fuzzy_output = re.sub("(card[0-9]+|-)", "", options["output"])
            if fuzzy_output in fuzzy_edid_map:
                edid = edid_map[list(edid_map.keys())[fuzzy_edid_map.index(fuzzy_output)]]
            elif "off" not in options:
                raise AutorandrException("Failed to find an EDID for output `%s' in setup file, required as `%s' "
                                         "is not off in config file." % (options["output"], options["output"]))
        output = options["output"]
        del options["output"]

        return XrandrOutput(output, edid, options)

    def edid_equals(self, other):
        "Compare to another XrandrOutput's edid and on/off-state, taking legacy autorandr behaviour (md5sum'ing) into account"
        if self.edid and other.edid:
            if len(self.edid) == 32 and len(other.edid) != 32 and not other.edid.startswith(XrandrOutput.EDID_UNAVAILABLE):
                return hashlib.md5(binascii.unhexlify(other.edid)).hexdigest() == self.edid
            if len(self.edid) != 32 and len(other.edid) == 32 and not self.edid.startswith(XrandrOutput.EDID_UNAVAILABLE):
                return hashlib.md5(binascii.unhexlify(self.edid)).hexdigest() == other.edid
            if "*" in self.edid:
                return fnmatch.fnmatch(other.edid, self.edid)
            elif "*" in other.edid:
                return fnmatch.fnmatch(self.edid, other.edid)
        return self.edid == other.edid

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        return self.edid_equals(other) and self.output == other.output and self.filtered_options == other.filtered_options

    def verbose_diff(self, other):
        "Compare to another XrandrOutput and return a list of human readable differences"
        diffs = []
        if not self.edid_equals(other):
            diffs.append("EDID `%s' differs from `%s'" % (self.short_edid, other.short_edid))
        if self.output != other.output:
            diffs.append("Output name `%s' differs from `%s'" % (self.output, other.output))
        if "off" in self.options and "off" not in other.options:
            diffs.append("The output is disabled currently, but active in the new configuration")
        elif "off" in other.options and "off" not in self.options:
            diffs.append("The output is currently enabled, but inactive in the new configuration")
        else:
            for name in set(chain.from_iterable((self.options.keys(), other.options.keys()))):
                if name not in other.options:
                    diffs.append("Option --%s %sis not present in the new configuration" %
                                 (name, "(= `%s') " % self.options[name] if self.options[name] else ""))
                elif name not in self.options:
                    diffs.append("Option --%s (`%s' in the new configuration) is not present currently" %
                                 (name, other.options[name]))
                elif self.options[name] != other.options[name]:
                    diffs.append("Option --%s %sis `%s' in the new configuration" %
                                 (name, "(= `%s') " % self.options[name] if self.options[name] else "", other.options[name]))
        return diffs


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
        bounds = (0, len(string))
        while bounds[0] != bounds[1]:
            half = int((bounds[0] + bounds[1]) / 2)
            if half == bounds[0]:
                break
            bounds = (half, bounds[1]) if regex.search(pattern, string[:half], partial=True) else (bounds[0], half - 1)
        partial_length = bounds[0]
        return ("Regular expression matched until position %d, ..'%s', and did not match from '%s'.." %
                (partial_length, string[max(0, partial_length - 20):partial_length],
                 string[partial_length:partial_length + 10]))
    except ImportError:
        pass
    return "Debug information would be available if the `regex' module was installed."


def parse_xrandr_output():
    "Parse the output of `xrandr --verbose' into a list of outputs"
    xrandr_output = os.popen("xrandr -q --verbose").read()
    if not xrandr_output:
        raise AutorandrException("Failed to run xrandr")

    # We are not interested in screens
    xrandr_output = re.sub("(?m)^Screen [0-9].+", "", xrandr_output).strip()

    # Split at output boundaries and instanciate an XrandrOutput per output
    split_xrandr_output = re.split("(?m)^([^ ]+ (?:(?:dis)?connected|unknown connection).*)$", xrandr_output)
    if len(split_xrandr_output) < 2:
        raise AutorandrException("No output boundaries found", report_bug=True)
    outputs = OrderedDict()
    modes = OrderedDict()
    for i in range(1, len(split_xrandr_output), 2):
        output_name = split_xrandr_output[i].split()[0]
        output, output_modes = XrandrOutput.from_xrandr_output("".join(split_xrandr_output[i:i + 2]))
        outputs[output_name] = output
        if output_modes:
            modes[output_name] = output_modes

    return outputs, modes


def load_profiles(profile_path):
    "Load the stored profiles"

    profiles = {}
    for profile in os.listdir(profile_path):
        config_name = os.path.join(profile_path, profile, "config")
        setup_name = os.path.join(profile_path, profile, "setup")
        if not os.path.isfile(config_name) or not os.path.isfile(setup_name):
            continue

        edids = dict([x.split() for x in (y.strip() for y in open(setup_name).readlines()) if x and x[0] != "#"])

        config = {}
        buffer = []
        for line in chain(open(config_name).readlines(), ["output"]):
            if line[:6] == "output" and buffer:
                config[buffer[0].strip().split()[-1]] = XrandrOutput.from_config_file(edids, "".join(buffer))
                buffer = [line]
            else:
                buffer.append(line)

        for output_name in list(config.keys()):
            if config[output_name].edid is None:
                del config[output_name]

        profiles[profile] = {
            "config": config,
            "path": os.path.join(profile_path, profile),
            "config-mtime": os.stat(config_name).st_mtime,
        }

    return profiles


def get_symlinks(profile_path):
    "Load all symlinks from a directory"

    symlinks = {}
    for link in os.listdir(profile_path):
        file_name = os.path.join(profile_path, link)
        if os.path.islink(file_name):
            symlinks[link] = os.readlink(file_name)

    return symlinks


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
        if not matches or any((name not in config.keys() for name in current_config.keys() if current_config[name].edid)):
            continue
        if matches:
            detected_profiles.append(profile_name)
    return detected_profiles


def profile_blocked(profile_path, meta_information=None):
    """Check if a profile is blocked.

    meta_information is expected to be an dictionary. It will be passed to the block scripts
    in the environment, as variables called AUTORANDR_<CAPITALIZED_KEY_HERE>.
    """
    return not exec_scripts(profile_path, "block", meta_information)


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


def call_and_retry(*args, **kwargs):
    """Wrapper around subprocess.call that retries failed calls.

    This function calls subprocess.call and on non-zero exit states,
    waits a second and then retries once. This mitigates #47,
    a timing issue with some drivers.
    """
    if "dry_run" in kwargs:
        dry_run = kwargs["dry_run"]
        del kwargs["dry_run"]
    else:
        dry_run = False
    kwargs_redirected = dict(kwargs)
    if not dry_run:
        if hasattr(subprocess, "DEVNULL"):
            kwargs_redirected["stdout"] = getattr(subprocess, "DEVNULL")
        else:
            kwargs_redirected["stdout"] = open(os.devnull, "w")
        kwargs_redirected["stderr"] = kwargs_redirected["stdout"]
    retval = subprocess.call(*args, **kwargs_redirected)
    if retval != 0:
        time.sleep(1)
        retval = subprocess.call(*args, **kwargs)
    return retval


def get_fb_dimensions(configuration):
    width = 0
    height = 0
    for output in configuration.values():
        if "off" in output.options or not output.edid:
            continue
        # This won't work with all modes -- but it's a best effort.
        o_width, o_height = map(int, output.options["mode"].split("x"))
        if "transform" in output.options:
            a, b, c, d, e, f, g, h, i = map(float, output.options["transform"].split(","))
            w = (g * o_width + h * o_height + i)
            x = (a * o_width + b * o_height + c) / w
            y = (d * o_width + e * o_height + f) / w
            o_width, o_height = x, y
        if "rotate" in output.options:
            if output.options["rotate"] in ("left", "right"):
                o_width, o_height = o_height, o_width
        if "pos" in output.options:
            o_left, o_top = map(int, output.options["pos"].split("x"))
            o_width += o_left
            o_height += o_top
        if "panning" in output.options:
            match = re.match("(?P<w>[0-9]+)x(?P<h>[0-9]+)(?:\+(?P<x>[0-9]+))?(?:\+(?P<y>[0-9]+))?.*", output.options["panning"])
            if match:
                detail = match.groupdict()
                o_width = int(detail.get("w")) + int(detail.get("x", "0"))
                o_height = int(detail.get("h")) + int(detail.get("y", "0"))
        width = max(width, o_width)
        height = max(height, o_height)
    return int(width), int(height)


def apply_configuration(new_configuration, current_configuration, dry_run=False):
    "Apply a configuration"
    outputs = sorted(new_configuration.keys(), key=lambda x: new_configuration[x].sort_key)
    if dry_run:
        base_argv = ["echo", "xrandr"]
    else:
        base_argv = ["xrandr"]

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
    # - If an active screen already has a transformation and remains active,
    #   the xrandr call fails with an invalid RRSetScreenSize parameter error.
    #   Update the configuration in 3 passes in that case.  (On Haswell graphics,
    #   at least.)
    # - Some implementations can not handle --transform at all, so avoid it unless
    #   necessary. (See https://github.com/phillipberndt/autorandr/issues/37)
    # - Some implementations can not handle --panning without specifying --fb
    #   explicitly, so avoid it unless necessary.
    #   (See https://github.com/phillipberndt/autorandr/issues/72)

    fb_dimensions = get_fb_dimensions(new_configuration)
    try:
        base_argv += ["--fb", "%dx%d" % fb_dimensions]
    except:
        # Failed to obtain frame-buffer size. Doesn't matter, xrandr will choose for the user.
        pass

    auxiliary_changes_pre = []
    disable_outputs = []
    enable_outputs = []
    remain_active_count = 0
    for output in outputs:
        if not new_configuration[output].edid or "off" in new_configuration[output].options:
            disable_outputs.append(new_configuration[output].option_vector)
        else:
            if "off" not in current_configuration[output].options:
                remain_active_count += 1

            option_vector = new_configuration[output].option_vector
            if xrandr_version() >= Version("1.3.0"):
                for option, off_value in (("transform", "none"), ("panning", "0x0")):
                    if option in current_configuration[output].options:
                        auxiliary_changes_pre.append(["--output", output, "--%s" % option, off_value])
                    else:
                        try:
                            option_index = option_vector.index("--%s" % option)
                            if option_vector[option_index + 1] == XrandrOutput.XRANDR_DEFAULTS[option]:
                                option_vector = option_vector[:option_index] + option_vector[option_index + 2:]
                        except ValueError:
                            pass

            enable_outputs.append(option_vector)

    # Perform pe-change auxiliary changes
    if auxiliary_changes_pre:
        argv = base_argv + list(chain.from_iterable(auxiliary_changes_pre))
        if call_and_retry(argv, dry_run=dry_run) != 0:
            raise AutorandrException("Command failed: %s" % " ".join(argv))

    # Disable unused outputs, but make sure that there always is at least one active screen
    disable_keep = 0 if remain_active_count else 1
    if len(disable_outputs) > disable_keep:
        argv = base_argv + list(chain.from_iterable(disable_outputs[:-1] if disable_keep else disable_outputs))
        if call_and_retry(argv, dry_run=dry_run) != 0:
            # Disabling the outputs failed. Retry with the next command:
            # Sometimes disabling of outputs fails due to an invalid RRSetScreenSize.
            # This does not occur if simultaneously the primary screen is reset.
            pass
        else:
            disable_outputs = disable_outputs[-1:] if disable_keep else []

    # If disable_outputs still has more than one output in it, one of the xrandr-calls below would
    # disable the last two screens. This is a problem, so if this would happen, instead disable only
    # one screen in the first call below.
    if len(disable_outputs) > 0 and len(disable_outputs) % 2 == 0:
        # In the context of a xrandr call that changes the display state, `--query' should do nothing
        disable_outputs.insert(0, ['--query'])

    # Enable the remaining outputs in pairs of two operations
    operations = disable_outputs + enable_outputs
    for index in range(0, len(operations), 2):
        argv = base_argv + list(chain.from_iterable(operations[index:index + 2]))
        if call_and_retry(argv, dry_run=dry_run) != 0:
            raise AutorandrException("Command failed: %s" % " ".join(argv))


def is_equal_configuration(source_configuration, target_configuration):
    """
        Check if all outputs from target are already configured correctly in source and
        that no other outputs are active.
    """
    for output in target_configuration.keys():
        if "off" in target_configuration[output].options:
            if (output in source_configuration and "off" not in source_configuration[output].options):
                return False
        else:
            if (output not in source_configuration) or (source_configuration[output] != target_configuration[output]):
                return False
    for output in source_configuration.keys():
        if "off" in source_configuration[output].options:
            if output in target_configuration and "off" not in target_configuration[output].options:
                return False
        else:
            if output not in target_configuration:
                return False
    return True


def add_unused_outputs(source_configuration, target_configuration):
    "Add outputs that are missing in target to target, in 'off' state"
    for output_name, output in source_configuration.items():
        if output_name not in target_configuration:
            target_configuration[output_name] = XrandrOutput(output_name, output.edid, {"off": None})


def remove_irrelevant_outputs(source_configuration, target_configuration):
    "Remove outputs from target that ought to be 'off' and already are"
    for output_name, output in source_configuration.items():
        if "off" in output.options:
            if output_name in target_configuration:
                if "off" in target_configuration[output_name].options:
                    del target_configuration[output_name]


def generate_virtual_profile(configuration, modes, profile_name):
    "Generate one of the virtual profiles"
    configuration = copy.deepcopy(configuration)
    if profile_name == "common":
        mode_sets = []
        for output, output_modes in modes.items():
            mode_set = set()
            if configuration[output].edid:
                for mode in output_modes:
                    mode_set.add((mode["width"], mode["height"]))
            mode_sets.append(mode_set)
        common_resolution = reduce(lambda a, b: a & b, mode_sets[1:], mode_sets[0])
        common_resolution = sorted(common_resolution, key=lambda a: int(a[0]) * int(a[1]))
        if common_resolution:
            for output in configuration:
                configuration[output].options = {}
                if output in modes and configuration[output].edid:
                    modes_sorted = sorted(modes[output], key=lambda x: 0 if x["preferred"] else 1)
                    modes_filtered = [x for x in modes_sorted if (x["width"], x["height"]) == common_resolution[-1]]
                    mode = modes_filtered[0]
                    configuration[output].options["mode"] = mode['name']
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
            if output in modes and configuration[output].edid:
                def key(a):
                    score = int(a["width"]) * int(a["height"])
                    if a["preferred"]:
                        score += 10**6
                    return score
                output_modes = sorted(modes[output], key=key)
                mode = output_modes[-1]
                configuration[output].options["mode"] = mode["name"]
                configuration[output].options["rate"] = mode["rate"]
                configuration[output].options["pos"] = pos_specifier % shift
                shift += int(mode[shift_index])
            else:
                configuration[output].options["off"] = None
    elif profile_name == "clone-largest":
        modes_unsorted = [output_modes[0] for output, output_modes in modes.items()]
        modes_sorted = sorted(modes_unsorted, key=lambda x: int(x["width"]) * int(x["height"]), reverse=True)
        biggest_resolution = modes_sorted[0]
        for output in configuration:
            configuration[output].options = {}
            if output in modes and configuration[output].edid:
                def key(a):
                    score = int(a["width"]) * int(a["height"])
                    if a["preferred"]:
                        score += 10**6
                    return score
                output_modes = sorted(modes[output], key=key)
                mode = output_modes[-1]
                configuration[output].options["mode"] = mode["name"]
                configuration[output].options["rate"] = mode["rate"]
                configuration[output].options["pos"] = "0x0"
                scale = max(float(biggest_resolution["width"]) / float(mode["width"]),
                            float(biggest_resolution["height"]) / float(mode["height"]))
                mov_x = (float(mode["width"]) * scale - float(biggest_resolution["width"])) / -2
                mov_y = (float(mode["height"]) * scale - float(biggest_resolution["height"])) / -2
                configuration[output].options["transform"] = "{},0,{},0,{},{},0,0,1".format(scale, mov_x, scale, mov_y)
            else:
                configuration[output].options["off"] = None
    elif profile_name == "off":
        for output in configuration:
            for key in list(configuration[output].options.keys()):
                del configuration[output].options[key]
            configuration[output].options["off"] = None
    return configuration


def print_profile_differences(one, another):
    "Print the differences between two profiles for debugging"
    if one == another:
        return
    print("| Differences between the two profiles:")
    for output in set(chain.from_iterable((one.keys(), another.keys()))):
        if output not in one:
            if "off" not in another[output].options:
                print("| Output `%s' is missing from the active configuration" % output)
        elif output not in another:
            if "off" not in one[output].options:
                print("| Output `%s' is missing from the new configuration" % output)
        else:
            for line in one[output].verbose_diff(another[output]):
                print("| [Output %s] %s" % (output, line))
    print("\\-")


def exit_help():
    "Print help and exit"
    print(help_text)
    for profile in virtual_profiles:
        name, description = profile[:2]
        description = [description]
        max_width = 78 - 18
        while len(description[0]) > max_width + 1:
            left_over = description[0][max_width:]
            description[0] = description[0][:max_width] + "-"
            description.insert(1, "  %-15s %s" % ("", left_over))
        description = "\n".join(description)
        print("  %-15s %s" % (name, description))
    sys.exit(0)


def exec_scripts(profile_path, script_name, meta_information=None):
    """"Run userscripts

    This will run all executables from the profile folder, and global per-user
    and system-wide configuration folders, named script_name or residing in
    subdirectories named script_name.d.

    If profile_path is None, only global scripts will be invoked.

    meta_information is expected to be an dictionary. It will be passed to the block scripts
    in the environment, as variables called AUTORANDR_<CAPITALIZED_KEY_HERE>.

    Returns True unless any of the scripts exited with non-zero exit status.
    """
    all_ok = True
    env = os.environ.copy()
    if meta_information:
        for key, value in meta_information.items():
            env["AUTORANDR_{}".format(key.upper())] = str(value)

    # If there are multiple candidates, the XDG spec tells to only use the first one.
    ran_scripts = set()

    user_profile_path = os.path.expanduser("~/.autorandr")
    if not os.path.isdir(user_profile_path):
        user_profile_path = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "autorandr")

    candidate_directories = [user_profile_path]
    for config_dir in os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":"):
        candidate_directories.append(os.path.join(config_dir, "autorandr"))
    if profile_path:
        candidate_directories.append(profile_path)

    for folder in candidate_directories:
        if script_name not in ran_scripts:
            script = os.path.join(folder, script_name)
            if os.access(script, os.X_OK | os.F_OK):
                try:
                    all_ok &= subprocess.call(script, env=env) != 0
                except:
                    raise AutorandrException("Failed to execute user command: %s" % (script,))
                ran_scripts.add(script_name)

        script_folder = os.path.join(folder, "%s.d" % script_name)
        if os.access(script_folder, os.R_OK | os.X_OK) and os.path.isdir(script_folder):
            for file_name in os.listdir(script_folder):
                check_name = "d/%s" % (file_name,)
                if check_name not in ran_scripts:
                    script = os.path.join(script_folder, file_name)
                    if os.access(script, os.X_OK | os.F_OK):
                        try:
                            all_ok &= subprocess.call(script, env=env) != 0
                        except:
                            raise AutorandrException("Failed to execute user command: %s" % (script,))
                        ran_scripts.add(check_name)

    return all_ok


def dispatch_call_to_sessions(argv):
    """Invoke autorandr for each open local X11 session with the given options.

    The function iterates over all processes not owned by root and checks
    whether they have DISPLAY and XAUTHORITY variables set. It strips the
    screen from any variable it finds (i.e. :0.0 becomes :0) and checks whether
    this display has been handled already. If it has not, it forks, changes
    uid/gid to the user owning the process, reuses the process's environment
    and runs autorandr with the parameters from argv.

    This function requires root permissions. It only works for X11 servers that
    have at least one non-root process running. It is susceptible for attacks
    where one user runs a process with another user's DISPLAY variable - in
    this case, it might happen that autorandr is invoked for the other user,
    which won't work. Since no other harm than prevention of automated
    execution of autorandr can be done this way, the assumption is that in this
    situation, the local administrator will handle the situation."""

    X11_displays_done = set()

    autorandr_binary = os.path.abspath(argv[0])
    backup_candidates = {}

    def fork_child_autorandr(pwent, process_environ):
        print("Running autorandr as %s for display %s" % (pwent.pw_name, process_environ["DISPLAY"]))
        child_pid = os.fork()
        if child_pid == 0:
            # This will throw an exception if any of the privilege changes fails,
            # so it should be safe. Also, note that since the environment
            # is taken from a process owned by the user, reusing it should
            # not leak any information.
            os.setgroups([])
            os.setresgid(pwent.pw_gid, pwent.pw_gid, pwent.pw_gid)
            os.setresuid(pwent.pw_uid, pwent.pw_uid, pwent.pw_uid)
            os.chdir(pwent.pw_dir)
            os.environ.clear()
            os.environ.update(process_environ)
            os.execl(autorandr_binary, autorandr_binary, *argv[1:])
            os.exit(1)
        os.waitpid(child_pid, 0)

    for directory in os.listdir("/proc"):
        directory = os.path.join("/proc/", directory)
        if not os.path.isdir(directory):
            continue
        environ_file = os.path.join(directory, "environ")
        if not os.path.isfile(environ_file):
            continue
        uid = os.stat(environ_file).st_uid

        # The following line assumes that user accounts start at 1000 and that
        # no one works using the root or another system account. This is rather
        # restrictive, but de facto default. Alternatives would be to use the
        # UID_MIN from /etc/login.defs or FIRST_UID from /etc/adduser.conf;
        # but effectively, both values aren't binding in any way.
        # If this breaks your use case, please file a bug on Github.
        if uid < 1000:
            continue

        process_environ = {}
        for environ_entry in open(environ_file).read().split("\0"):
            name, sep, value = environ_entry.partition("=")
            if name and sep:
                if name == "DISPLAY" and "." in value:
                    value = value[:value.find(".")]
                process_environ[name] = value

        if "DISPLAY" not in process_environ:
            # Cannot work with this environment, skip.
            continue

        # To allow scripts to detect batch invocation (especially useful for predetect)
        process_environ["AUTORANDR_BATCH_PID"] = str(os.getpid())
        process_environ["UID"] = str(uid)

        display = process_environ["DISPLAY"]

        if "XAUTHORITY" not in process_environ:
            # It's very likely that we cannot work with this environment either,
            # but keep it as a backup just in case we don't find anything else.
            backup_candidates[display] = process_environ
            continue

        if display not in X11_displays_done:
            try:
                pwent = pwd.getpwuid(uid)
            except KeyError:
                # User has no pwd entry
                continue

            fork_child_autorandr(pwent, process_environ)
            X11_displays_done.add(display)

    # Run autorandr for any users/displays which didn't have a process with
    # XAUTHORITY set.
    for display, process_environ in backup_candidates.items():
        if display not in X11_displays_done:
            try:
                pwent = pwd.getpwuid(int(process_environ["UID"]))
            except KeyError:
                # User has no pwd entry
                continue

            fork_child_autorandr(pwent, process_environ)
            X11_displays_done.add(display)


def enabled_monitors(config):
    monitors = []
    for monitor in config:
        if "--off" in config[monitor].option_vector:
            continue
        monitors.append(monitor)
    return monitors


def read_config(options, directory):
    """Parse a configuration config.ini from directory and merge it into
    the options dictionary"""
    config = configparser.ConfigParser()
    config.read(os.path.join(directory, "settings.ini"))
    if config.has_section("config"):
        for key, value in config.items("config"):
            options.setdefault("--%s" % key, value)

def main(argv):
    try:
        opts, args = getopt.getopt(argv[1:], "s:r:l:d:cfh",
                                   ["batch", "dry-run", "change", "default=", "save=", "remove=", "load=",
                                    "force", "fingerprint", "config", "debug", "skip-options=", "help",
                                    "current", "detected", "version"])
    except getopt.GetoptError as e:
        print("Failed to parse options: {0}.\n"
              "Use --help to get usage information.".format(str(e)),
              file=sys.stderr)
        sys.exit(posix.EX_USAGE)

    options = dict(opts)

    if "-h" in options or "--help" in options:
        exit_help()

    if "--version" in options:
        print("autorandr " + __version__)
        sys.exit(0)

    if "--current" in options and "--detected" in options:
        print("--current and --detected are mutually exclusive.", file=sys.stderr)
        sys.exit(posix.EX_USAGE)

    # Batch mode
    if "--batch" in options:
        if ("DISPLAY" not in os.environ or not os.environ["DISPLAY"]) and os.getuid() == 0:
            dispatch_call_to_sessions([x for x in argv if x != "--batch"])
        else:
            print("--batch mode can only be used by root and if $DISPLAY is unset")
        return
    if "AUTORANDR_BATCH_PID" in os.environ:
        user = pwd.getpwuid(os.getuid())
        user = user.pw_name if user else "#%d" % os.getuid()
        print("autorandr running as user %s (started from batch instance)" % user)

    profiles = {}
    profile_symlinks = {}
    try:
        # Load profiles from each XDG config directory
        # The XDG spec says that earlier entries should take precedence, so reverse the order
        for directory in reversed(os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")):
            system_profile_path = os.path.join(directory, "autorandr")
            if os.path.isdir(system_profile_path):
                profiles.update(load_profiles(system_profile_path))
                profile_symlinks.update(get_symlinks(system_profile_path))
                read_config(options, system_profile_path)
        # For the user's profiles, prefer the legacy ~/.autorandr if it already exists
        # profile_path is also used later on to store configurations
        profile_path = os.path.expanduser("~/.autorandr")
        if not os.path.isdir(profile_path):
            # Elsewise, follow the XDG specification
            profile_path = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "autorandr")
        if os.path.isdir(profile_path):
            profiles.update(load_profiles(profile_path))
            profile_symlinks.update(get_symlinks(profile_path))
            read_config(options, profile_path)
        # Sort by descending mtime
        profiles = OrderedDict(sorted(profiles.items(), key=lambda x: -x[1]["config-mtime"]))
    except Exception as e:
        raise AutorandrException("Failed to load profiles", e)

    profile_symlinks = {k: v for k, v in profile_symlinks.items() if v in (x[0] for x in virtual_profiles) or v in profiles}

    exec_scripts(None, "predetect")
    config, modes = parse_xrandr_output()

    if "--fingerprint" in options:
        output_setup(config, sys.stdout)
        sys.exit(0)

    if "--config" in options:
        output_configuration(config, sys.stdout)
        sys.exit(0)

    if "--skip-options" in options:
        skip_options = [y[2:] if y[:2] == "--" else y for y in (x.strip() for x in options["--skip-options"].split(","))]
        for profile in profiles.values():
            for output in profile["config"].values():
                output.set_ignored_options(skip_options)
        for output in config.values():
            output.set_ignored_options(skip_options)

    if "-s" in options:
        options["--save"] = options["-s"]
    if "--save" in options:
        if options["--save"] in (x[0] for x in virtual_profiles):
            raise AutorandrException("Cannot save current configuration as profile '%s':\n"
                                     "This configuration name is a reserved virtual configuration." % options["--save"])
        try:
            profile_folder = os.path.join(profile_path, options["--save"])
            save_configuration(profile_folder, config)
            exec_scripts(profile_folder, "postsave", {
                "CURRENT_PROFILE": options["--save"],
                "PROFILE_FOLDER": profile_folder,
                "MONITORS": ":".join(enabled_monitors(config)),
            })
        except Exception as e:
            raise AutorandrException("Failed to save current configuration as profile '%s'" % (options["--save"],), e)
        print("Saved current configuration as profile '%s'" % options["--save"])
        sys.exit(0)

    if "-r" in options:
        options["--remove"] = options["-r"]
    if "--remove" in options:
        if options["--remove"] in (x[0] for x in virtual_profiles):
            raise AutorandrException("Cannot remove profile '%s':\n"
                                     "This configuration name is a reserved virtual configuration." % options["--remove"])
        if options["--remove"] not in profiles.keys():
            raise AutorandrException("Cannot remove profile '%s':\n"
                                     "This profile does not exist." % options["--remove"])
        try:
            remove = True
            profile_folder = os.path.join(profile_path, options["--remove"])
            profile_dirlist = os.listdir(profile_folder)
            profile_dirlist.remove("config")
            profile_dirlist.remove("setup")
            if profile_dirlist:
                print("Profile folder '%s' contains the following additional files:\n"
                      "---\n%s\n---" % (options["--remove"], "\n".join(profile_dirlist)))
                response = input("Do you really want to remove profile '%s'? If so, type 'yes': " % options["--remove"]).strip()
                if response != "yes":
                    remove = False
            if remove is True:
                shutil.rmtree(profile_folder)
                print("Removed profile '%s'" % options["--remove"])
            else:
                print("Profile '%s' was not removed" % options["--remove"])
        except Exception as e:
            raise AutorandrException("Failed to remove profile '%s'" % (options["--remove"],), e)
        sys.exit(0)

    detected_profiles = find_profiles(config, profiles)
    load_profile = False

    if "-l" in options:
        options["--load"] = options["-l"]
    if "--load" in options:
        load_profile = options["--load"]
    elif len(args) == 1:
        load_profile = args[0]
    else:
        # Find the active profile(s) first, for the block script (See #42)
        current_profiles = []
        for profile_name in profiles.keys():
            configs_are_equal = is_equal_configuration(config, profiles[profile_name]["config"])
            if configs_are_equal:
                current_profiles.append(profile_name)
        block_script_metadata = {
            "CURRENT_PROFILE": "".join(current_profiles[:1]),
            "CURRENT_PROFILES": ":".join(current_profiles)
        }

        for profile_name in profiles.keys():
            if profile_blocked(os.path.join(profile_path, profile_name), block_script_metadata):
                if "--current" not in options and "--detected" not in options:
                    print("%s (blocked)" % profile_name)
                continue
            props = []
            if profile_name in detected_profiles:
                props.append("(detected)")
                if ("-c" in options or "--change" in options) and not load_profile:
                    load_profile = profile_name
            elif "--detected" in options:
                continue
            if profile_name in current_profiles:
                props.append("(current)")
            elif "--current" in options:
                continue
            if "--current" in options or "--detected" in options:
                print("%s" % (profile_name, ))
            else:
                print("%s%s%s" % (profile_name, " " if props else "", " ".join(props)))
            if not configs_are_equal and "--debug" in options and profile_name in detected_profiles:
                print_profile_differences(config, profiles[profile_name]["config"])

    if "-d" in options:
        options["--default"] = options["-d"]
    if not load_profile and "--default" in options and ("-c" in options or "--change" in options):
        load_profile = options["--default"]

    if load_profile:
        if load_profile in profile_symlinks:
            if "--debug" in options:
                print("'%s' symlinked to '%s'" % (load_profile, profile_symlinks[load_profile]))
            load_profile = profile_symlinks[load_profile]

        if load_profile in (x[0] for x in virtual_profiles):
            load_config = generate_virtual_profile(config, modes, load_profile)
            scripts_path = os.path.join(profile_path, load_profile)
        else:
            try:
                profile = profiles[load_profile]
                load_config = profile["config"]
                scripts_path = profile["path"]
            except KeyError:
                raise AutorandrException("Failed to load profile '%s': Profile not found" % load_profile)
            if load_profile in detected_profiles and detected_profiles[0] != load_profile:
                update_mtime(os.path.join(scripts_path, "config"))
        add_unused_outputs(config, load_config)
        if load_config == dict(config) and "-f" not in options and "--force" not in options:
            print("Config already loaded", file=sys.stderr)
            sys.exit(0)
        if "--debug" in options and load_config != dict(config):
            print("Loading profile '%s'" % load_profile)
            print_profile_differences(config, load_config)

        remove_irrelevant_outputs(config, load_config)

        try:
            if "--dry-run" in options:
                apply_configuration(load_config, config, True)
            else:
                script_metadata = {
                    "CURRENT_PROFILE": load_profile,
                    "PROFILE_FOLDER": scripts_path,
                    "MONITORS": ":".join(enabled_monitors(load_config)),
                }
                exec_scripts(scripts_path, "preswitch", script_metadata)
                if "--debug" in options:
                    print("Going to run:")
                    apply_configuration(load_config, config, True)
                apply_configuration(load_config, config, False)
                exec_scripts(scripts_path, "postswitch", script_metadata)
        except AutorandrException as e:
            raise AutorandrException("Failed to apply profile '%s'" % load_profile, e, e.report_bug)
        except Exception as e:
            raise AutorandrException("Failed to apply profile '%s'" % load_profile, e, True)

        if "--dry-run" not in options and "--debug" in options:
            new_config, _ = parse_xrandr_output()
            if not is_equal_configuration(new_config, load_config):
                print("The configuration change did not go as expected:")
                print_profile_differences(new_config, load_config)

    sys.exit(0)


def exception_handled_main(argv=sys.argv):
    try:
        main(sys.argv)
    except AutorandrException as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if not len(str(e)):  # BdbQuit
            print("Exception: {0}".format(e.__class__.__name__))
            sys.exit(2)

        print("Unhandled exception ({0}). Please report this as a bug at "
              "https://github.com/phillipberndt/autorandr/issues.".format(e),
              file=sys.stderr)
        raise


if __name__ == '__main__':
    exception_handled_main()
