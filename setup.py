#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import os
import sys
from setuptools import setup

DOCDIR = '/usr/share/doc/smoker'
INITDIR = '/etc/rc.d/init.d'

# Parameters for build
params = {
    # This package is named gdc-smoker on Pypi, use it on register or upload actions
    'name' : 'gdc-smoker' if 'upload' in sys.argv or 'register' in sys.argv else 'smoker',
    'version': '2.0.1',
    'packages': [
        'smoker',
        'smoker.server',
        'smoker.server.plugins',
        'smoker.client',
        'smoker.client.out_junit',
        'smoker.client.plugins',
        'smoker.logger',
        'smoker.util'
        ],
    'scripts': [
        'bin/smokerd.py',
        'bin/smokercli.py',
        'bin/check_smoker_plugin.py',
        ],
    'url': 'https://github.com/gooddata/smoker',
    'download_url': 'https://github.com/gooddata/smoker',
    'license': 'BSD',
    'author': 'GoodData Corporation',
    'author_email': 'python@gooddata.com',
    'maintainer': 'Filip Pytloun',
    'maintainer_email': 'filip@pytloun.cz',
    'description': 'Smoke Testing Framework',
    'long_description': open('DESCRIPTION.md').read(),
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Monitoring',
    ],
    'platforms': ['POSIX'],
    'provides': ['smoker'],
    'install_requires': ['PyYAML', 'argparse', 'simplejson', 'psutil', 'setproctitle', 'Flask-RESTful'],
    'data_files': [
        (INITDIR, ['rc.d/init.d/smokerd']),
        (DOCDIR, ['etc/smokerd-example.yaml', 'etc/smokercli-example.yaml'])
    ]
}

setup(**params)
