#!/usr/bin/env python3

from __future__ import print_function

import argparse
import traceback

import sys,os

common = os.path.abspath(os.path.join(sys.path[0], '..','common'))

if not common in sys.path:
    sys.path.append(common)
from kicad_mod import *

from print_color import *
from rules_footprint import __all__ as all_rules
from rules_footprint import *
from rules_footprint.rule import KLCRule
from rulebase import logError

# enable windows wildcards
from glob import glob



def check_library(filename, rules, metrics, args):
    if not os.path.exists(filename):
        printer.red('File does not exist: %s' % filename)
        return (1, 0)

    if not filename.endswith('.kicad_mod'):
        printer.red('File is not a .kicad_mod : %s' % filename)
        return (1, 0)

    lib_name = os.path.dirname(filename).split(os.path.sep)[-1].replace('.pretty', '')

    if args.errors:
        module = KicadMod(filename)
    else:
        try:
            module = KicadMod(filename)
        except Exception as e:
            printer.red('Could not parse footprint: %s. (%s)' % (filename, e))
            if args.verbose:
                #printer.red("Error: " + str(e))
                traceback.print_exc()
            return (1, 0)

    if args.rotate!=0:
        module.rotateFootprint(int(args.rotate))
        printer.green('rotated footprint by {deg} degrees'.format(deg=int(args.rotate)))

    # check which kind of tests we want to run
    if args.unittest:
        (ec, wc) = do_unittest(module, rules, metrics)
    else:
        (ec, wc) = do_rulecheck(module, rules, metrics)

    # done checking the footpint
    metrics.append('{lib}.errors {n}'.format(lib=module.name, n=ec))
    metrics.append('{lib}.warnings {n}'.format(lib=module.name, n=wc))
    return (ec, wc)


def do_unittest(footprint, rules, metrics):
    error_count = 0
    m = re.match(r'(\w+)__(.+)__(.+)', footprint.name)
    if not m:
        printer.red("Test '{foot}' could not be parsed".format(foot=footprint.name))
        return (1, 0)
    unittest_result = m.group(1)
    unittest_rule = m.group(2)
    unittest_descrp = m.group(3)
    for rule in rules:
        rule = rule(footprint, args)
        if unittest_rule == rule.name:
            rule.check()
            if unittest_result == 'Fail' and rule.errorCount == 0:
                printer.red("Test '{foot}' failed".format(foot=footprint.name))
                error_count += 1
                continue
            if unittest_result == 'Warn' and rule.warningCount() == 0:
                printer.red("Test '{foot}' failed".format(foot=footprint.name))
                error_count += 1
                continue
            if unittest_result == 'Pass' and (rule.warningCount() != 0 or rule.errorCount != 0):
                printer.red("Test '{foot}' failed".format(foot=footprint.name))
                error_count += 1
                continue
            printer.green("Test '{foot}' passed".format(foot=footprint.name))

        else:
           continue
    return (error_count, warning_count)

def do_rulecheck(module, rules, metrics):
    ec = 0
    wc = 0
    no_warnings = True
    output = []
    first = True

    for rule in rules:
        rule = rule(module,args)
        if verbosity > 2:
            printer.white("Checking rule " + rule.name)
        rule.check()

        # count errors
        if rule.hasErrors():
            ec += rule.errorCount
        if rule.hasWarnings:
            wc += rule.warningCount()

        if args.nowarnings and not rule.hasErrors():
            continue

        if rule.hasOutput():
            if first:
                printer.green("Checking footprint '{fp}':".format(fp=module.name))
                first = False

            printer.yellow("Violating " + rule.name + " - " + rule.url, indentation=2)
            rule.processOutput(printer, args.verbose, args.silent)

        elif rule.hasErrors():
            if args.log:
                logError(args.log, rule.name, lib_name, module.name)

            if args.fix:
                if args.fixmore and rule.needsFixMore:
                    rule.fixmore()
                rule.fix()
                rule.processOutput(printer, args.verbose, args.silent)
                rule.recheck()

    # No messages?
    if first:
        if not args.silent:
            printer.green("Checking footprint '{fp}' - No errors".format(fp=module.name))

    if ((args.fix or args.fixmore) and ec > 0) or args.rotate!=0:
        module.save()

    return (ec, wc)

parser = argparse.ArgumentParser(description='Checks KiCad footprint files (.kicad_mod) against KiCad Library Convention (KLC) rules. You can find the KLC at http://kicad.org/libraries/klc/')
parser.add_argument('kicad_mod_files', nargs='+')
parser.add_argument('--fix', help='fix the violations if possible', action='store_true')
parser.add_argument('--fixmore', help='fix additional violations, not covered by --fix (e.g. rectangular courtyards), implies --fix!', action='store_true')
parser.add_argument('--rotate', help='rotate the whole footprint clockwise by the given number of degrees', action='store', default=0)
parser.add_argument('-r', '--rule', help='specify single rule to check (default = check all rules)', action='store')
parser.add_argument('--nocolor', help='does not use colors to show the output', action='store_true')
parser.add_argument('-v', '--verbose', help='Enable verbose output. -v shows brief information, -vv shows complete information', action='count')
parser.add_argument('-s', '--silent', help='skip output for footprints passing all checks', action='store_true')
parser.add_argument('-e', '--errors', help='Do not suppress fatal parsing errors', action='store_true')
parser.add_argument('-l', '--log', help="Path to JSON file to log error information")
parser.add_argument('-w', '--nowarnings', help='Hide warnings (only show errors)', action='store_true')
parser.add_argument('-u', '--unittest', help='unit test mode (to be used with test-footprints)', action='store_true')
parser.add_argument('-m', '--metrics', help='generate a metrics.txt file', action='store_true')

args = parser.parse_args()
if args.fixmore:
    args.fix=True

printer = PrintColor(use_color=not args.nocolor)

# Set verbosity globally
verbosity = 0
if args.verbose:
    verbosity = args.verbose
KLCRule.verbosity = verbosity

# create a list of rules that should be checked
if args.rule:
    selected_rules = args.rule.split(",")
else:
    selected_rules = None

rules = []
for r in all_rules:
    r_name = r.replace('_', '.')
    if selected_rules == None or r_name in selected_rules:
        rules.append(globals()[r].Rule)

# figure out which files should be checked
files = []
for f in args.kicad_mod_files:
    files += glob(f)

if len(files) == 0:
    printer.red("File argument invalid: {f}".format(f=args.kicad_mod_files))
    sys.exit(1)

# now iterate over all files and check them
metrics = []
error_count = 0
warning_count = 0
for filename in files:
    (ec, wc) = check_library(filename, rules, metrics, args)
    error_count += ec
    warning_count += wc

# done checking all files
if args.metrics or args.unittest:
  metrics_file = file2 = open(r"metrics.txt","a+")
  for line in metrics:
    metrics_file.write(line + "\n")
  metrics_file.close()

if args.fix:
    printer.light_red('Some files were updated - ensure that they still load correctly in KiCad')

sys.exit(0 if error_count == 0 else -1)
