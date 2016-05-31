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
PROCESSES = [0]
HOSTNAME = socket.gethostname()


def rest_api_response(k, **kwargs):
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
    plugin_list = ['Hostname', 'Uptime', 'Uname']
    url = 'http://%s:8086' % HOSTNAME
    result = {
        url + '/': about_response,
        url + '/processes': dict(),
        url + '/plugins': plugins_response,
    }
    if k in result.keys():
        if k == url + '/processes' and kwargs.get('data'):
            data = ast.literal_eval(kwargs.get('data'))
            if True in [x in plugin_list for x in data['process']['plugins']]:
                location = len(PROCESSES)
                process = {
                    "href": "processes/%s" % location,
                    "plugins": [x for x in data['process']['plugins']]
                }
                PROCESSES.append(process)
                return_value = {
                    'asyncTask': {
                        'link': {
                            'poll': '/processes/%s' % location
                        }
                    }
                }
            else:
                return abort(500)
        elif k == url + '/processes' and not kwargs.get('data'):
            return_value = PROCESSES if len(PROCESSES) > 1 else dict()
        else:
            return_value = result[k]  # Return static result

    elif re.search('%s/processes/[0-9]+' % url, k):
        if k == '%s/processes/0' % url:
            return abort(404)
        proc_number = int(re.search('%s/processes/([0-9]+)' % url, k).group(1))
        return_value = {
            "plugins": {
                "items": [force_plugin_run_response[x]
                          for x in PROCESSES[proc_number]['plugins']]
            }
        }

    else:
        return abort(404)  # Return 404 if k don't match predefine pattern

    fp = '%s/%s.tmp' % (TMP_DIR, generate_unique_file())
    open(fp, 'w').write(json.dumps(return_value))
    return open(fp)

about_response = {
    'about': {
        'host': HOSTNAME,
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
    'Uname': {
        'plugin': {
            'name': 'Uname',
            'links': {
                'self': '/plugins/Uname'
            },
            'nextRun': '2016-05-31T11:11:06.126684',
            'forcedResult': {
                'status': 'WARN',
                'lastRun': '2016-05-31T13:11:33.684257',
                'forced': True,
                'messages': {
                    'info': [],
                    'warn': [
                        'Skipped because of maintenance in progress'
                    ],
                    'error': []
                },
                'componentResults': None,
                'action': None
            },
            'lastResult': {
                'status': 'WARN',
                'lastRun': '2016-05-31T13:11:33.684257',
                'forced': True,
                'messages': {
                    'info': [],
                    'warn': [
                        'Skipped because of maintenance in progress'
                    ],
                    'error': []
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
                'MaintenanceLock': '/tmp/smokerd.lock',
                'gid': 'default',
                'Command': None,
                'Timeout': 30,
                'Action': None,
                'Template': None,
                'History': 10
            }
        }
    },
    'Uptime': {
        'plugin': {
            'name': 'Uptime',
            'links': {
                'self': '/plugins/Uptime'
            },
            'nextRun': '2016-05-31T11:11:06.126856',
            'forcedResult': {
                'status': 'OK',
                'lastRun': '2016-05-31T13:12:10.554044',
                'forced': True,
                'messages': {
                    'info': [
                        '13:12:10 up 7 days,    2:08,    1 user,'
                        '    load average: 0.74, 0.44, 0.36'
                    ],
                    'warn': [],
                    'error': []
                },
                'componentResults': None,
                'action': None
            },
            'lastResult': {
                'status': 'OK',
                'lastRun': '2016-05-31T13:12:10.554044',
                'forced': True,
                'messages': {
                    'info': [
                        '13:12:10 up 7 days,    2:08,    1 user,'
                        '    load average: 0.74, 0.44, 0.36'
                    ],
                    'warn': [],
                    'error': []
                },
                'componentResults': None,
                'action': None
            },
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
            }
        }
    },
    'Hostname': {
        'plugin': {
            'name': 'Hostname',
            'links': {
                'self': '/plugins/Hostname'
            },
            'nextRun': '2016-05-31T11:11:06.127003',
            'forcedResult': {
                'status': 'ERROR',
                'lastRun': '2016-05-31T13:12:46.880849',
                'forced': True,
                'messages': {
                    'info': [],
                    'warn': [],
                    'error': [
                        '/bin/sh: 1: InvalidCommand: not found'
                    ]
                },
                'componentResults': None,
                'action': None
            },
            'lastResult': {
                'status': 'ERROR',
                'lastRun': '2016-05-31T13:12:46.880849',
                'forced': True,
                'messages': {
                    'info': [],
                    'warn': [],
                    'error': [
                        '/bin/sh: 1: InvalidCommand: not found'
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
                'Module': None,
                'MaintenanceLock': None,
                'gid': 'default',
                'Command': 'InvalidCommand',
                'Timeout': 30,
                'Action': None,
                'Template': None,
                'History': 10
            }
        }
    }
}

plugins_response = {
    'plugins': {
        'items': [
            {
                'plugin': {
                    'lastResult': {
                        'status': 'WARN',
                        'lastRun': '2016-05-31T15:32:53.187552',
                        'forced': True,
                        'messages': {
                            'info': [],
                            'warn': [
                                'Skipped because of maintenance in progress'
                            ],
                            'error': []
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
                        'MaintenanceLock': '/tmp/smokerd.lock',
                        'gid': 'default',
                        'Command': None,
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    },
                    'nextRun': '2016-05-31T15:31:35.191518'
                }
            },
            {
                'plugin': {
                    'lastResult': {
                        'status': 'OK',
                        'lastRun': '2016-05-31T15:32:53.194612',
                        'forced': True,
                        'messages': {
                            'info': [
                                '15:32:53 up 7 days, 4:29, 1 user,'
                                ' load average: 1.07, 1.32, 1.28'
                            ],
                            'warn': [],
                            'error': []
                        },
                        'componentResults': None,
                        'action': None
                    },
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
                    'nextRun': '2016-05-31T15:31:35.191695'
                }
            },
            {
                'plugin': {
                    'lastResult': {
                        'status': 'ERROR',
                        'lastRun': '2016-05-31T15:32:53.189058',
                        'forced': True,
                        'messages': {
                            'info': [],
                            'warn': [],
                            'error': [
                                '/bin/sh: 1: InvalidCommand: not found'
                            ]
                        },
                        'componentResults': None,
                        'action': None
                    },
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
                        'Command': 'InvalidCommand',
                        'Timeout': 30,
                        'Action': None,
                        'Template': None,
                        'History': 10
                    },
                    'nextRun': '2016-05-31T15:31:35.191841'
                }
            }
        ]
    }
}

tap_result_all_plugins = [
    '1..1',
    'not ok 1 - %s' % HOSTNAME,
    '	1..3',
    '	not ok 1 - Hostname',
    '	---',
    '		- error:',
    '			- /bin/sh: 1: InvalidCommand: not found',
    '	...',
    '	ok 2 - Uname',
    '	---',
    '		- warn:',
    '			- Skipped because of maintenance in progress',
    '	...',
    '	ok 3 - Uptime',
    '	---',
    '		- info:',
    '			- 15:32:53 up 7 days, 4:29, 1 user, load average: 1.07, 1.32, 1.28',
    '	...'
]

tap_result_uptime_hostname = [
    '1..1',
    'not ok 1 - %s' % HOSTNAME,
    '	1..2',
    '	not ok 1 - Hostname',
    '	---',
    '		- error:',
    '			- /bin/sh: 1: InvalidCommand: not found',
    '	...',
    '	ok 2 - Uptime',
    '	---',
    '		- info:',
    '			- 15:32:53 up 7 days, 4:29, 1 user, load average: 1.07, 1.32, 1.28',
    '	...',
]

tap_result_uptime_uname = [
    '1..1',
    'ok 1 - %s' % HOSTNAME,
    '	1..2',
    '	ok 1 - Uname',
    '	---',
    '		- warn:',
    '			- Skipped because of maintenance in progress',
    '	...',
    '	ok 2 - Uptime',
    '	---',
    '		- info:',
    '			- 15:32:53 up 7 days, 4:29, 1 user, load average: 1.07, 1.32, 1.28',
    '	...'
]

tap_result_hostname_uname = [
    '1..1',
    'not ok 1 - %s' % HOSTNAME,
    '	1..2',
    '	not ok 1 - Hostname',
    '	---',
    '		- error:',
    '			- /bin/sh: 1: InvalidCommand: not found',
    '	...',
    '	ok 2 - Uname',
    '	---',
    '		- warn:',
    '			- Skipped because of maintenance in progress',
    '	...',
]

xml_result_all_plugins = [
    '',
    '  <testsuites name="All">',
    '    <testsuite name="node %s" timestamp="2016-05-31 15:32:53" hostname="%s">' % (HOSTNAME, HOSTNAME),
    '      <testcase classname="%s.Hostname" name="Hostname">' % HOSTNAME,
    '        <error message="/bin/sh: 1: InvalidCommand: not found"></error></testcase>',
    '      <testcase classname="%s.Uname" name="Uname">' % HOSTNAME,
    '        <system-out message="Skipped because of maintenance in progress"></system-out></testcase>',
    '      <testcase classname="%s.Uptime" name="Uptime"></testcase></testsuite></testsuites>' % HOSTNAME
]

xml_result_uptime_uname = [
    '',
    '  <testsuites name="All">',
    '    <testsuite name="node %s" timestamp="2016-05-31 15:32:53" hostname="%s">' % (HOSTNAME, HOSTNAME),
    '      <testcase classname="%s.Uname" name="Uname">' % HOSTNAME,
    '        <system-out message="Skipped because of maintenance in progress"></system-out></testcase>',
    '      <testcase classname="%s.Uptime" name="Uptime"></testcase></testsuite></testsuites>' % HOSTNAME
]

xml_result_uptime_hostname = [
    '',
    '  <testsuites name="All">',
    '    <testsuite name="node %s" timestamp="2016-05-31 15:32:53" hostname="%s">' % (HOSTNAME, HOSTNAME),
    '      <testcase classname="%s.Hostname" name="Hostname">' % HOSTNAME,
    '        <error message="/bin/sh: 1: InvalidCommand: not found"></error></testcase>',
    '      <testcase classname="%s.Uptime" name="Uptime"></testcase></testsuite></testsuites>' % HOSTNAME
]

xml_result_hostname_uname = [
    '',
    '  <testsuites name="All">',
    '    <testsuite name="node %s" timestamp="2016-05-31 15:32:53" hostname="%s">' % (HOSTNAME, HOSTNAME),
    '      <testcase classname="%s.Hostname" name="Hostname">' % HOSTNAME,
    '        <error message="/bin/sh: 1: InvalidCommand: not found"></error></testcase>',
    '      <testcase classname="%s.Uname" name="Uname">' % HOSTNAME,
    '        <system-out message="Skipped because of maintenance in progress"></system-out></testcase></testsuite></testsuites>'
]
