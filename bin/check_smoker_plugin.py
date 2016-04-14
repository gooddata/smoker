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

UNKNOWN = "UNKNOWN"
ERROR = "ERROR"
WARN = "WARN"
OK = "OK"

# Don't log into console, use only syslog
smoker.logger.init(syslog=True, console=False)
lg = logging.getLogger('check_smoker_plugin')

parser = argparse.ArgumentParser(description='Smoker Nagios plugin')
parser.add_argument('-f', '--force', dest='force', action='store_true',
                    help="Force plugins run (otherwise just print last results)")
parser.add_argument('--category', default=None, help='The category of tests to run')
parser.add_argument('--component', default=None, help='The tests component to run')
parser.add_argument('--health', default=False, dest='health', action='store_true', help="Run only healthchecks")
parser.add_argument('plugin', default=None, nargs='*', help="Plugin to check")
args = parser.parse_args()


def parse_issue(plugin_result):
    out = "smoke test: %s " % plugin_result['name']
    for component in plugin_result['lastResult']['componentResults']:
        if component['componentResult']['status'] != OK:
            out += "%s: %s; " % ( component['componentResult']['name'], component['componentResult']['status'])
    if len(out) > 1024:
        out = "smoke test: %s returns huge error output, see smoker logs for details" % plugin_result['name']
    return out


def main():
    client = Client(['localhost'])
    plugins = None

    if args.plugin:
        if args.category or args.component or args.health:
            lg.warn("Plugins specified by name, ignoring --category, --component and --health")

        plugins = client.get_plugins([args.plugin])
    elif args.category or args.component or args.health:
        filter = []
        if args.category:
            filter.append({'key': 'Category', 'value': args.category})
        if args.component:
            filter.append({'key': 'Component', 'value': args.component})
        if args.health:
            filter.append({'key': 'Type', 'value': 'healthCheck'})
        plugins = client.get_plugins(filter)
    else:
        nagios.exit_unknown("invalid startup configuration - neither plugin nor --category nor --component "
                            "nor --health specified")

    # No plugin found
    if not plugins:
        if args.plugin:
            message = "plugin %s not found" % args.plugin
        else:
            message = "no plugin found by category %s and component %s, health: %s" % \
                      (args.category, args.component, args.health)
        nagios.exit_unknown(message)

    if args.force:
        plugins = client.force_run(plugins, progress=False)

    status_methods_pairs = [(ERROR, nagios.exit_critical), (UNKNOWN, nagios.exit_unknown),
                            (WARN, nagios.exit_warning), (OK, nagios.exit_ok)]

    # Manage plugin result. We can't return much data to Nagios, so just say if it's alright or not
    results = dict((s, []) for s, _ in status_methods_pairs)

    for plugin in plugins.values()[0]['plugins'].itervalues():
        plugin_name = plugin['name']
        if not plugin['lastResult']:
            results[UNKNOWN].append({'name': plugin_name, 'message': "plugin has no last result"})
        else:
            last_status = plugin['lastResult']['status']

            if last_status in [ERROR, WARN, OK]:
                try:
                    results[last_status].append({'name': plugin_name,
                                                 'message': plugin['lastResult']['messages'][last_status.lower()][0]})
                except (KeyError, IndexError, TypeError):
                    if last_status == OK:
                        results[last_status].append(
                            {'name': plugin_name,
                             'message': "smoke test %s succeeded at %s" %
                                        (plugin['name'], plugin['lastResult']['lastRun'])})
                    else:
                        results[last_status].append({'name': plugin_name, 'message': parse_issue(plugin)})
            else:
                results[UNKNOWN].append({'name': plugin_name,
                                         'message': "unknown status %s at %s" %
                                                    (plugin['lastResult']['status'], plugin['lastResult']['lastRun'])})

    for status, exit_method in status_methods_pairs:
        if results[status]:
            if len(plugins.values()[0]['plugins']) == 1:
                # if only one plugin has been executed, do not print summary
                exit_method(results[status][0]['message'])
            else:
                summary = ', '.join(["%s: %s" % (s, len(results[s])) for s, _ in status_methods_pairs if results[s]])
                messages = ['\n'.join(["%s - %s - %s" % (s, item['name'], item['message']) for item in list])
                            for s, list in results.iteritems() if list]
                exit_method("%s\n%s" % (summary, '\n'.join(messages)))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        lg.exception(e)
        nagios.exit_unknown(e)
