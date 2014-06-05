#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

"""
Check Smoker plugin and force it's run by option.
Return Nagios-friendly result. We can't send much data so just send if it's alright or not or print first line of
standard non-component messages if present.
"""

import argparse
import logging

from smoker.client import Client
import smoker.util.nagios as nagios
import smoker.logger


# Don't log into console, use only syslog
smoker.logger.init(syslog=True, console=False)
lg = logging.getLogger('check_smoker_plugin')

parser = argparse.ArgumentParser(description='Smoker Nagios plugin')
parser.add_argument('-f', '--force', dest='force', action='store_true', help="Force plugins run (otherwise just print last results)")
parser.add_argument('plugin', help="Plugin to check")
args = parser.parse_args()

def ParseIssue(plugin_result):
    out = "smoke test: %s " % plugin_result['name']
    for component in plugin_result['lastResult']['componentResults']:
        if component['componentResult']['status'] != 'OK':
            out += "%s: %s; " % ( component['componentResult']['name'], component['componentResult']['status'] )
    if len(out) > 1024:
        out = "smoke test: %s returns huge error output, see smoker logs for details" % plugin_result['name']
    return out

def main():
    client = Client(['localhost'])
    plugins = client.get_plugins([[args.plugin]])

    # No plugin found
    if not plugins:
        nagios.exit_unknown("plugin %s not found" % args.plugin)

    if args.force:
        plugins = client.force_run(plugins, progress=False)

    # Manage plugin result. We can't return much data to Nagios, so just say if it's alright or not
    for plugin in plugins.values()[0]['plugins'].itervalues():
        if not plugin['lastResult']:
            # No result?! -> UNKNOWN
            nagios.exit_unknown("plugin has no last result")
        elif plugin['lastResult']['status'] == 'OK':
            try:
                nagios.exit_ok(plugin['lastResult']['messages']['ok'][0])
            except (KeyError, IndexError, TypeError):
                nagios.exit_ok("smoke test %s succeeded at %s" % ( plugin['name'], plugin['lastResult']['lastRun']) )
        elif plugin['lastResult']['status'] == 'WARN':
            try:
                nagios.exit_warning(plugin['lastResult']['messages']['warn'][0])
            except (KeyError, IndexError, TypeError):
                nagios.exit_warning(ParseIssue(plugin))
        elif plugin['lastResult']['status'] == 'ERROR':
            try:
                nagios.exit_critical(plugin['lastResult']['messages']['error'][0])
            except (KeyError, IndexError, TypeError):
                nagios.exit_critical(ParseIssue(plugin))
        else:
            nagios.exit_unknown("unknown status %s at %s" % (plugin['lastResult']['status'], plugin['lastResult']['lastRun']))

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        lg.exception(e)
        nagios.exit_unknown(e)
