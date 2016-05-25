#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

import ast
import datetime
from flask.ext.restful import abort
import json
import os
import re
import socket


def generate_unique_file():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')

TMP_DIR = (os.path.dirname(os.path.realpath(__file__)) + '/.tmp')
PROCESSES = []


def rest_api_response(k, **kwargs):
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
    plugin_list = ['Hostname', 'Uptime', 'Uname']
    url = 'http://%s:8086' % socket.gethostname()
    result = {
        url + '/': about_response,
        url + '/processes': dict(),
        url + '/plugins': plugins_response,
    }
    if k in result.keys():
        if k == url + '/processes' and kwargs.get('data'):
            data = ast.literal_eval(kwargs.get('data'))
            if False in [x not in plugin_list
                         for x in data['process']['plugins']]:
                location = len(PROCESSES) + 1
                process = {
                    "href": "processes/%s" % location,
                    "plugins": [x for x in data['process']['plugins']]
                }
                PROCESSES.append(process)
                data = {
                    'asyncTask': {
                        'link': {
                            'poll': '/processes/%s' % location
                        }
                    }
                }
                return_value = data
            else:
                return abort(500)
        elif k == url + '/processes' and not kwargs.get('data'):
            return_value = PROCESSES
        else:
            return_value = result[k]  # Return static result
    elif re.search('%s/processes/[0-9]+' % url, k):
        return_value = force_plugin_run_response

    else:
        return abort(404)
    fp = '%s/%s.tmp' % (TMP_DIR, generate_unique_file())
    open(fp, 'w').write(json.dumps(return_value))
    return open(fp)

about_response = {
    'about': {
        'host': socket.gethostname(),
        'links': [
            {
                'href': '/plugins',
                'methods': 'GET',
                'rel': 'plugins',
                'title': 'Show details about all plugins'
            },
            {
                'href': '/processes',
                'methods': 'GET, POST',
                'rel': 'processes',
                'title': 'Force plugin run'
                }
            ],
        'title': 'Smoker daemon API'
    }
}

links = {
    'processes': {
        'href': '/processes',
        'methods': 'GET, POST',
        'rel': 'processes',
        'title': 'Force plugin run'
    },
    'plugins': {
        'href': '/plugins',
        'methods': 'GET',
        'rel': 'plugins',
        'title': 'Show details about all plugins'
    }
}

force_plugin_run_response = {
    'plugins': {
        'items': [
            {
                'plugin': {
                    'name': 'Uname',
                    'links': {
                        'self': '/plugins/Uname'
                    },
                    'nextRun': '2016-05-24T11:28:23.500085',
                    'forcedResult': {
                        'status': 'OK',
                        'lastRun': '2016-05-24T11:32:23.215592',
                        'forced': True,
                        'messages': {
                            'info': [
                                'Linux lhv 3.13.0-83-generic #127-Ubuntu SMP '
                                'Fri Mar 11 00:25:37 UTC 2016 x86_64'
                            ],
                            'warn': [

                            ],
                            'error': [

                            ]
                        },
                        'componentResults': None,
                        'action': None
                    },
                    'lastResult': {
                        'status': 'OK',
                        'lastRun': '2016-05-24T11:32:23.215592',
                        'forced': None,
                        'messages': {
                            'info': [
                                'Linux lhv 3.13.0-83-generic #127-Ubuntu SMP '
                                'Fri Mar 11 00:25:37 UTC 2016 x86_64'
                            ],
                            'warn': [

                            ],
                            'error': [

                            ]
                        },
                        'componentResults': None,
                        'action': None
                    },
                    'parameters': {
                        'Category': 'system',
                        'Parser': None,
                        'uid': 'default',
                        'Interval': 1,
                        'Module': 'smoker.server.plugins.uname',
                        'MaintenanceLock': None,
                        'gid': 'default',
                        'Command': None,
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    }
                }
            }
        ]
    }
}

plugins_response = {
    'plugins': {
        'items': [
            {
                'plugin': {
                    'lastResult': {
                        'status': 'OK',
                        'lastRun': '2016-05-24T14:21:25.097693',
                        'forced': True,
                        'messages': {
                            'info': [
                                'Linux lhv 3.13.0-83-generic #127-Ubuntu SMP '
                                'Fri Mar 11 00:25:37 UTC 2016 x86_64'
                            ],
                            'warn': [

                            ],
                            'error': [

                            ]
                        },
                        'componentResults': None,
                        'action': None
                    },
                    'links': {
                        'self': '/plugins/Uname'
                    },
                    'name': 'Uname',
                    'parameters': {
                        'Category': 'system',
                        'Parser': None,
                        'uid': 'default',
                        'Interval': 1,
                        'Module': 'smoker.server.plugins.uname',
                        'MaintenanceLock': None,
                        'gid': 'default',
                        'Command': None,
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    },
                    'nextRun': '2016-05-24T11:28:23.500085'
                }
            },
            {
                'plugin': {
                    'lastResult': None,
                    'links': {
                        'self': '/plugins/Hostname'
                    },
                    'name': 'Hostname',
                    'parameters': {
                        'Category': 'system',
                        'Parser': None,
                        'uid': 'default',
                        'Interval': 1,
                        'Module': None,
                        'MaintenanceLock': None,
                        'gid': 'default',
                        'Command': 'hostname',
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    },
                    'nextRun': '2016-05-24T11:28:23.500203'
                }
            },
            {
                'plugin': {
                    'lastResult': None,
                    'links': {
                        'self': '/plugins/Uptime'
                    },
                    'name': 'Uptime',
                    'parameters': {
                        'Category': 'monitoring',
                        'Parser': None,
                        'uid': 'default',
                        'Interval': 1,
                        'Module': None,
                        'MaintenanceLock': None,
                        'gid': 'default',
                        'Command': 'uptime',
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    },
                    'nextRun': '2016-05-24T11:28:23.500307'
                }
            }
        ]
    }
}
