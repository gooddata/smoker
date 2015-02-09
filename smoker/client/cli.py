#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Client tool for GDC Smoker daemon

See pydoc for command line tool smoker.py
"""

import argparse
import datetime
import glob
import logging
import os
import simplejson
import sys
import yaml

from smoker.client import Client
import smoker.logger
from smoker.client.out_junit import plugins_to_xml
from smoker.util.tap import TapTest, Tap


smoker.logger.init(syslog=False)
lg = logging.getLogger('smokercli')


COLORS = {
    'default' : '\033[0;0m',
    'magenta' : '\033[1;35m',
    'yellow'  : '\033[1;33m',
    'gold' : '\033[0;33m',
    'red'  : '\033[1;31m',
    'blue' : '\033[1;34m',
    'green': '\033[1;32m',
    'cyan' : '\033[1;36m',
    'gray' : '\033[0;37m',
}


CONFIG_FILE = '/etc/smokercli.yaml'


def _get_plugins():
    """
    Get list of available host discovery plugin module names
    """

    plugins = []
    conf_file = os.path.expanduser('~/.smokercli.yaml')

    if not os.path.exists(conf_file):
        conf_file = CONFIG_FILE

    if not os.path.exists(conf_file):
        return plugins

    with open(conf_file) as f:
        config = yaml.safe_load(f)

    if config and 'plugin_paths' in config:
        paths = config['plugin_paths']
    else:
        raise Exception('Invalid config file')


    for path in paths:
        try:
            module = __import__(path)
        except ImportError:
            raise Exception('Invalid config file')

        toplevel = os.path.dirname(module.__file__)
        submodule = '/'.join(path.split('.')[1:])
        plugin_dir = os.path.join(toplevel, submodule, '*.py')
        modules = [os.path.basename(name)[:-3] for name in
                   glob.glob(plugin_dir)]
        modules.remove('__init__')
        plugins += ['%s.%s' % (path, name) for name in modules]

    return plugins


def _get_plugin_arguments(name):
    """
    Get list of host discovery plugin specific cmdline arguments

    :param name: plugin module name
    """
    try:
        plugin = __import__(name, globals(), locals(), ['HostDiscoveryPlugin'])
    except ImportError as e:
        lg.error("Can't load module %s: %s" % (name, e))
        raise
    return plugin.HostDiscoveryPlugin.arguments


def _add_plugin_arguments(parser):
    """
    Add host discovery plugin specific options to the cmdline argument parser

    :param parser: argparse.ArgumentParser instance
    """

    plugins = _get_plugins()
    if not plugins:
        return
    argument_group = parser.add_argument_group('Plugin arguments')

    for plugin in plugins:
        args = _get_plugin_arguments(plugin)
        for argument in args:
            argument_group.add_argument(*argument.args, **argument.kwargs)


def _run_discovery_plugin(name, args):
    """
    Run the host discovery plugin
    :param name: plugin module name
    :param args: attribute namespace
    :return: discovered hosts list
    """
    try:
        this_plugin = __import__(name, globals(), locals(),
                                 ['HostDiscoveryPlugin'])
    except ImportError as e:
        lg.error("Can't load module %s: %s" % (name, e))
        raise

    plugin=this_plugin.HostDiscoveryPlugin()
    return plugin.get_hosts(args)


def _host_discovery(args):
    """
    Run all the discovery plugins

    :param args: attribute namespace
    :return: discovered hosts list
    """
    discovered = []

    for plugin in _get_plugins():
        hosts = _run_discovery_plugin(plugin, args)
        if hosts:
            discovered += hosts

    return discovered


def main():
    """
    Main entrance
    """
    parser = argparse.ArgumentParser(description='Smoker client tool', add_help=False)

    # Action arguments
    group_action = parser.add_argument_group('Action switchers')
    group_action.add_argument('-f', '--force', dest='force', action='store_true', help="Force plugins run (otherwise just print last results)")
    group_action.add_argument('-l', '--list', dest='list', action='store_true', help="List plugins")
    group_action.add_argument('-h', '--help', dest='help', action='store_true', help="Show this help and exit")

    # Host arguments
    group_main = parser.add_argument_group('Target host switchers')
    group_main.add_argument('-s', '--hosts', dest='hosts', nargs='+', help="Hosts with running smokerd (default localhost)")

    # Filtering options
    # List of plugins
    group_filters = parser.add_argument_group('Filters')
    group_filters.add_argument('-p', '--plugins', dest='plugins', nargs='+', help="Filter plugins by names, can't be used with --filter option")
    group_filters.add_argument('--exclude-plugins', dest='exclude_plugins', nargs='+', help="Exclude plugins by names")

    # Other filters
    group_filters.add_argument('--filter', dest='filter', default=[], nargs='+', help="Filter plugins by it's parameters, eg. --filter 'Category connectors'")
    group_filters.add_argument('--exclude', action='store_true', help="Negative filters (exclude) - currently works only for one filter")
    group_filters.add_argument('--category', help="Filter plugins by Category parameter")
    group_filters.add_argument('--component', help="Filter plugins by Component parameter (eg. server)")
    group_filters.add_argument('--health', action='store_true', help="Filter plugins by Type healthCheck")
    group_filters.add_argument('--smoke', action='store_true', help="Filter plugins by Type smokeTest")

    # Plugin state filters
    group_filters.add_argument('--filter-status', dest='filter_status', default=[], nargs='+', help="Filter plugins by it's state, eg. --filter-state ERROR WARN")
    group_filters.add_argument('--nook', dest='state_nook', action='store_true', help="Only non-OK plugins (ERROR, WARN, UNKNOWN). Can't be used together with --filter-state")
    group_filters.add_argument('--error', dest='state_error', action='store_true', help="Only ERROR. Can't be used together with --filter-state")
    group_filters.add_argument('--warn', '--warning', dest='state_warn', action='store_true', help="Only WARN. Can't be used together with --filter-state")
    group_filters.add_argument('--unknown', dest='state_unknown', action='store_true', help="Only UNKNOWN. Can't be used together with --filter-state")
    group_filters.add_argument('--ok', dest='state_ok', action='store_true', help="Only OK. Can't be used together with --filter-state")

    # Output switchers
    group_output = parser.add_argument_group('Output switchers')
    group_output.add_argument('-o', '--pretty', dest='pretty', default='normal', help="Output format: minimal / normal / long / full / raw / json / tap / xml")
    group_output.add_argument('--no-colors', dest='no_colors', action='store_true', help="Don't use colors in output")
    group_output.add_argument('--no-progress', dest='no_progress', action='store_true', help="Don't show progress bar")
    group_output.add_argument('-v', '--verbose', dest='verbose', action='store_true', help="Be verbose")
    group_output.add_argument('-d', '--debug', dest='debug', action='store_true', help="Debug output")
    group_output.add_argument('--junit-config-file', dest='junit_config_file', help="Name of configuration file for junit xml formatter")

    _add_plugin_arguments(parser)
    args = parser.parse_args()

    # Set log level and set args.no_progress option
    if args.verbose:
        lg.setLevel(logging.INFO)
        args.no_progress = True

    if args.debug:
        lg.setLevel(logging.DEBUG)
        args.no_progress = True

    if args.help:
        parser.print_help()
        sys.exit(0)

    if args.pretty == 'minimal':
        # Minimal output (only host and errored plugins)
        if not args.no_colors:
            format_host   = {
                'OK'    : '%(gold)s{name:<34}%(default)s [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : '%(gold)s{name:<34}%(default)s [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : '%(gold)s{name:<34}%(default)s [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : '%(gold)s{name:<34}%(default)s [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin = {
                'OK'    : '',
                'WARN'  : '- {name:<32} [%(yellow)s{lastResult[status]}%(default)s]   (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'ERROR' : '- {name:<32} [%(red)s{lastResult[status]}%(default)s] (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'UNKNOWN' : '- {name:<32} [%(magenta)s{lastResult[status]}%(default)s]'  % COLORS
            }
            format_plugin_component = {
                'OK'    : '',
                'WARN'  : ' -- {name:<30} [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : ' -- {name:<30} [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : ' -- {name:<30} [%(magenta)s{status}%(default)s]'  % COLORS,
            }
        else:
            format_host   = '{name:<34} [{status}]'
            format_plugin = {
                'OK'    : '',
                'WARN'  : '- {name:<32} [{lastResult[status]}] ({lastResult[lastRun]})',
                'ERROR' : '- {name:<32} [{lastResult[status]}] ({lastResult[lastRun]})',
                'UNKNOWN' : '- {name:<32} [{lastResult[status]}]'
            }
            format_plugin_component = {
                'OK'    : '',
                'WARN'  : ' -- {name:<30} [{status}]',
                'ERROR' : ' -- {name:<30} [{status}]',
                'UNKNOWN' : ' -- {name:<30} [{status}]',
            }

        format_plugin_msg = ''
        format_plugin_component_msg = ''
        format_plugin_run = ''
        format_plugin_param = ''
    elif args.pretty == 'normal':
        # Normal output (host and it's plugins without component results)
        if not args.no_colors:
            format_host   = {
                'OK'    : '%(gold)s{name:<34}%(default)s [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : '%(gold)s{name:<34}%(default)s [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : '%(gold)s{name:<34}%(default)s [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : '%(gold)s{name:<34}%(default)s [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin = {
                'OK'   : '- {name:<32} [%(green)s{lastResult[status]}%(default)s]    (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'WARN' : '- {name:<32} [%(yellow)s{lastResult[status]}%(default)s]   (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'ERROR': '- {name:<32} [%(red)s{lastResult[status]}%(default)s] (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'UNKNOWN': '- {name:<32} [%(magenta)s{lastResult[status]}%(default)s]'  % COLORS
            }
            format_plugin_msg = {
                'info'  : '',
                'warn'  : '  [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '  [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
            format_plugin_component = {
                'OK'    : '',
                'WARN'  : ' -- {name:<30} [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : ' -- {name:<30} [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : ' -- {name:<30} [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin_component_msg = {
                'info'  : '',
                'warn'  : '    [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '    [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
        else:
            format_host   = '{name:<34} [{status}]'
            format_plugin = '- {name:<32} [{lastResult[status]}] ({lastResult[lastRun]})'
            format_plugin_msg = {
                'info'  : '',
                'warn'  : '  [{level}] {msg}',
                'error' : '  [{level}] {msg}',
            }
            format_plugin_component = {
                'OK'    : '',
                'WARN'  : ' -- {name:<30} [{status}]',
                'ERROR' : ' -- {name:<30} [{status}]',
                'UNKNOWN' : ' -- {name:<30} [{status}]',
            }
            format_plugin_component_msg = {
                'info'  : '',
                'warn'  : '    [{level}] {msg}',
                'error' : '    [{level}] {msg}',
            }

        format_plugin_run = ''
        format_plugin_param = ''
    elif args.pretty == 'long':
        if not args.no_colors:
            format_host   = {
                'OK'    : '%(gold)s{name:<34}%(default)s [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : '%(gold)s{name:<34}%(default)s [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : '%(gold)s{name:<34}%(default)s [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : '%(gold)s{name:<34}%(default)s [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin = {
                'OK'   : '- {name:<32} [%(green)s{lastResult[status]}%(default)s]    (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'WARN' : '- {name:<32} [%(yellow)s{lastResult[status]}%(default)s]   (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'ERROR': '- {name:<32} [%(red)s{lastResult[status]}%(default)s]    (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'UNKNOWN': '- {name:<32} [%(magenta)s{lastResult[status]}%(default)s]'  % COLORS
            }
            format_plugin_msg = {
                'info'  : '  [%(blue)s{level}%(default)s] {msg}'  % COLORS,
                'warn'  : '  [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '  [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
            format_plugin_component = {
                'OK'    : ' -- {name:<30} [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : ' -- {name:<30} [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : ' -- {name:<30} [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : ' -- {name:<30} [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin_component_msg = {
                'info'  : '    [%(blue)s{level}%(default)s] {msg}'  % COLORS,
                'warn'  : '    [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '    [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
        else:
            format_host   = '{name:<34} [{status}]'
            format_plugin = '- {name:<32} [{lastResult[status]}] ({lastResult[lastRun]})'
            format_plugin_msg = '  [{level}] {msg}'
            format_plugin_component = ' -- {name:<30} [{status}]'
            format_plugin_component_msg = '    [{level}] {msg}'

        format_plugin_run = ''
        format_plugin_param = ''
    elif args.pretty == 'full':
        if not args.no_colors:
            format_host   = {
                'OK'    : '%(gold)s{name:<34}%(default)s [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : '%(gold)s{name:<34}%(default)s [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : '%(gold)s{name:<34}%(default)s [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : '%(gold)s{name:<34}%(default)s [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin = {
                'OK'   : '- {name:<32} [%(green)s{lastResult[status]}%(default)s]    (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'WARN' : '- {name:<32} [%(yellow)s{lastResult[status]}%(default)s]   (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'ERROR': '- {name:<32} [%(red)s{lastResult[status]}%(default)s]    (%(gray)s{lastResult[lastRun]}%(default)s)'  % COLORS,
                'UNKNOWN': '- {name:<32} [%(magenta)s{lastResult[status]}%(default)s]'  % COLORS
            }
            format_plugin_msg = {
                'info'  : '  [%(blue)s{level}%(default)s] {msg}'  % COLORS,
                'warn'  : '  [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '  [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
            format_plugin_component = {
                'OK'    : ' -- {name:<30} [%(green)s{status}%(default)s]'  % COLORS,
                'WARN'  : ' -- {name:<30} [%(yellow)s{status}%(default)s]'  % COLORS,
                'ERROR' : ' -- {name:<30} [%(red)s{status}%(default)s]'  % COLORS,
                'UNKNOWN' : ' -- {name:<30} [%(magenta)s{status}%(default)s]'  % COLORS,
            }
            format_plugin_component_msg = {
                'info'  : '    [%(blue)s{level}%(default)s] {msg}'  % COLORS,
                'warn'  : '    [%(yellow)s{level}%(default)s] {msg}'  % COLORS,
                'error' : '    [%(red)s{level}%(default)s] {msg}'  % COLORS,
            }
        else:
            format_host   = '{name:<34} [{status}]'
            format_plugin = '- {name:<32} [{lastResult[status]}] ({lastResult[lastRun]})'
            format_plugin_msg = '  [{level}] {msg}'
            format_plugin_component = ' -- {name:<30} [{status}]'
            format_plugin_component_msg = '    [{level}] {msg}'

        format_plugin_run = '  Last run: {lastResult[lastRun]!s}\n  Next run: {nextRun!s}'
        format_plugin_param = '  {key:<10} {value}'
    elif args.pretty in ['raw', 'json', 'tap', 'xml']:
        # Raw and special outputs doesn't need formatting
        pass
    else:
        lg.error("Invalid pretty output %s" % args.pretty)
        sys.exit(1)

    # Plugins list and filter can't be set together
    if args.filter and args.plugins:
        lg.error("Plugins list and filters can't be used together")
        sys.exit(1)

    # Setup custom filters
    if args.category:
        args.filter.append('Category %s' % args.category)

    if args.component:
        args.filter.append('Component %s' % args.component)

    # Health checks and smoke tests together? Don't add filter
    if args.health or args.smoke:
        if args.health:
            args.filter.append('Type healthCheck')

        if args.smoke:
            args.filter.append('Type smokeTest')

    # Setup plugins filter
    filters = []
    if args.filter:
        for f in args.filter:
            filter = {}
            try:
                filter = {
                    'key'  : f.split(' ')[0],
                    'value': f.split(' ')[1]
                }
            except:
                lg.error("Invalid filter parameter format!")
                sys.exit(1)

            filters.append(filter)
    elif args.plugins:
        filters.append(args.plugins)

    # Setup state filters
    states = []
    if args.filter_status:
        states = args.filter_status
    elif args.state_nook:
        states = ['ERROR', 'WARN', 'UNKNOWN']
    else:
        if args.state_ok:
            states.append('OK')
        if args.state_error:
            states.append('ERROR')
        if args.state_warn:
            states.append('WARN')
        if args.state_unknown:
            states.append('UNKNOWN')

    # State list cannot be empty
    if not states:
        states = ['OK', 'ERROR', 'WARN', 'UNKNOWN']
    # Add status filter
    filters.append(('status', states))

    hosts = ['localhost']
    discovered_hosts = _host_discovery(args)
    if args.hosts:
        hosts = args.hosts
        if discovered_hosts:
            hosts += discovered_hosts
    elif discovered_hosts:
        hosts = discovered_hosts

    # Initialize Client
    client = Client(hosts)
    plugins = client.get_plugins(filters, filters_negative=args.exclude, exclude_plugins=args.exclude_plugins)

    # No plugins found
    if not plugins:
        lg.error("No plugins found")
        sys.exit(1)

    # List plugins only (parameter --force is ignored)
    if args.list:
        plugins_tuple = plugins.get_host_plugins()

        if plugins.count_hosts() > 1:
            # We have more hosts than 1, print structure like:
            # server1/httpd
            # server2/crond
            for host, plugin in plugins_tuple:
                print "%s/%s" % (host['name'], plugin['name'])
        else:
            # Print only plugin-by-line structure without hostname
            for host, plugin in plugins_tuple:
                print "%s" % plugin['name']
        sys.exit(0)

    # Force plugins run
    # set progress=False if --no-progress parameter is set
    if args.force:
        plugins = client.force_run(plugins, progress=False if args.no_progress == True else True)

    # Print raw output
    if args.pretty == 'raw':
        from pprint import pprint
        pprint(plugins)
        sys.exit(0)
    elif args.pretty == 'json':
        # We need custom encoder to encode datetime objects
        class JSONEncoder(simplejson.JSONEncoder):
            """
            JSON encoder that converts datetime.datetime object to isoformat string
            """
            def default(self, obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                return simplejson.JSONEncoder.default(self, obj)

        print simplejson.dumps(plugins, cls=JSONEncoder)
        sys.exit(0)
    elif args.pretty == 'tap':
        dump = dump_tap(plugins)
        # Convert mixed string into ascii to workaround UnicodeEncodeError
        # shouldn't be needed in Python 3
        print dump.encode('ascii', 'ignore')
        sys.exit(0)
    elif args.pretty == 'xml':
        dump = plugins_to_xml(plugins, args.junit_config_file)
        print dump
        sys.exit(0)

    # Print result
    output = []
    hosts_printed = []
    for host, plugin in plugins.get_host_plugins():
        # Print host if not already printed
        if host['name'] not in hosts_printed:
            # Add empty line if any previous host
            if hosts_printed: output.append(" ")
            if isinstance(format_host, dict):
                output.append(format_host[host['status']].format(**host))
            else:
                output.append(format_host.format(**host))
            hosts_printed.append(host['name'])

        # Print plugin
        if not isinstance(plugin, dict):
            # Not a plugin
            continue
        if isinstance(format_plugin, basestring):
            output.append(format_plugin.format(**plugin))
        else:
            output.append(format_plugin[plugin['lastResult']['status']].format(**plugin))

        # Print last and next plugin run
        output.append(format_plugin_run.format(**plugin))

        # Print last and next plugin run
        for key, value in plugin['parameters'].iteritems():
            output.append(format_plugin_param.format(key=key, value=value))

        # Print plugin messages
        if plugin['lastResult']['messages']:
            # For each message level
            for level, message in plugin['lastResult']['messages'].iteritems():
                # For each message
                for msg in message:
                    if isinstance(format_plugin_msg, basestring):
                        output.append(format_plugin_msg.format(level=level, msg=msg.encode('utf8')))
                    else:
                        output.append(format_plugin_msg[level].format(level=level, msg=msg.encode('utf8')))

        # Print component result
        if plugin['lastResult']['componentResults']:
            for component in plugin['lastResult']['componentResults']:
                component = component['componentResult']
                if isinstance(format_plugin_component, basestring):
                    output.append(format_plugin_component.format(**component))
                else:
                    output.append(format_plugin_component[component['status']].format(**component))

                # Print component messages
                if component['messages']:
                    # For each message level
                    for level, message in component['messages'].iteritems():
                        # For each message
                        for msg in message:
                            if isinstance(format_plugin_component_msg, basestring):
                                output.append(format_plugin_component_msg.format(level=level, msg=msg.encode('utf8')))
                            else:
                                output.append(format_plugin_component_msg[level].format(level=level, msg=msg.encode('utf8')))

    for line in output:
        if line:
            print line

def dump_tap(plugins):
    """
    Dump plugins result to TAP
    Take OK and also WARN statuses as ok
    Print only error and warn results
    """
    tap = Tap()

    for name in sorted(plugins):
        host = plugins[name]
        if host['status'] in ['OK', 'WARN']:
            host_ok = True
        else:
            host_ok = False

        tap_host = TapTest(name, host_ok)
        tap.add_test(tap_host)

        # For each host's plugin
        for key in sorted(host['plugins']):
            plugin = host['plugins'][key]
            if not plugin['lastResult']:
                plugin_ok = False
            else:
                if plugin['lastResult']['status'] in ['OK', 'WARN']:
                    plugin_ok = True
                else:
                    plugin_ok = False

            # Add messages to test result
            messages = []
            if plugin['lastResult']:
                if plugin['lastResult']['messages']:
                    messages = plugin['lastResult']['messages']

            tap_plugin = TapTest(plugin['name'], plugin_ok, messages)
            tap_host.add_subtest(tap_plugin)

            if plugin['lastResult'] and plugin['lastResult']['componentResults']:
                # For each component result
                for component in plugin['lastResult']['componentResults']:
                    component = component['componentResult']
                    if component['status'] in ['OK', 'WARN']:
                        component_ok = True
                    else:
                        component_ok = False

                    # Add messages to test result
                    messages = []
                    if component['messages']:
                        if component['messages']:
                            messages = component['messages']

                    tap_component = TapTest(component['name'], component_ok, messages)
                    tap_plugin.add_subtest(tap_component)

    return tap.dump()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
