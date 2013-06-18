#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Client tool for GDC Smoker daemon

USAGE
    Action switchers:
      -f, --force           Force plugins run (otherwise just print last results)
      -l, --list            List plugins
      -h, --help            Show this help and exit

    Target host switchers:
      -s HOSTS [HOSTS ...], --hosts HOSTS [HOSTS ...]
                            Hosts with running smokerd (default localhost)

    Filters:
      -p PLUGINS [PLUGINS ...], --plugins PLUGINS [PLUGINS ...]
                            Filter plugins by names, can't be used with --filter
                            option
      --exclude-plugins EXCLUDE_PLUGINS [EXCLUDE_PLUGINS ...]
                            Exclude plugins by names
      --filter FILTER [FILTER ...]
                            Filter plugins by it's parameters, eg. --filter
                            'Category connectors'
      --exclude             Negative filters (exclude) - currently works only for one filter
      --category CATEGORY   Filter plugins by Category parameter
      --component COMPONENT
                            Filter plugins by Component parameter (eg. server)
      --health              Filter plugins by Type healthCheck
      --smoke               Filter plugins by Type smokeTest

      --filter-status FILTER_STATUS [FILTER_STATUS ...]
                            Filter plugins by it's state, eg. --filter-state ERROR WARN
      --nook                Only non-OK plugins (ERROR, WARN, UNKNOWN). Can't be
                            used together with --filter-state
      --error               Only ERROR. Can't be used together with --filter-state
      --warn, --warning     Only WARN. Can't be used together with --filter-state
      --unknown             Only UNKNOWN. Can't be used together with --filter-state
      --ok                  Only OK. Can't be used together with --filter-state

    Output switchers:
      -o PRETTY, --pretty PRETTY
                            Output format: minimal / normal / long / full / raw /
                            json / tap
      --no-colors           Don't use colors in output
      -v, --verbose         Be verbose
      -d, --debug           Debug output

OUTPUT
    Use parameter -o / --pretty to control output
        minimal - host, errored and warned plugins and errored and warned components + error and warning messages
        normal  - host, all plugins, errored and warned components + error and warning messages
        long    - host, all plugins and component results + all messages
        full    - host, all plugins and component results + all messages + plugin info

        raw     - pprint output
        json    - simplejson output

    It's formatted in following scheme
        {format_host}
        for each plugin:
            {format_plugin}
            for each message:
                {format_plugin_run}
                {format_plugin_params}
                {format_plugin_msg}

            for each component:
                {format_plugin_component}
                for each message:
                    {format_plugin_component_msg}

EXAMPLES
    Show results on current host with minimal output
        smoker.py -o minimal

    The same as above with normal output but force immediate run
        smoker.py -f

    Force run of all plugins and print normal output for 2 specific nodes
        smoker.py -f -s server1 server2

    Get results for plugins with category services, component apache
        smoker.py --category services --component apache

    Get results for plugin Uname and Uptime and don't use colors
        smoker.py -p Uname Uptime --no-colors

    Run only smoke tests (no health checks - you should always use --smoke or --health)
        smoker.py --smoke -f

    Run again only smoke tests that failed
        smoker.py --smoke --nook -f

    List plugins that are smoke tests and doesn't name selinux and rpm
        smoker.py --smoke --exclude-plugins selinux rpm --list

    Exclude plugins of category workers
        smoker.py --exclude --category services
"""

import sys
from smoker.client.cli import main

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
