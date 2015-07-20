#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import os
import sys
from setuptools import setup

# This package is named gdc-smoker on Pypi (register or upload actions)
if 'upload' in sys.argv or 'register' in sys.argv:
    name = 'gdc-smoker'
else:
    name = 'smoker'

# Parameters for build
params = {
    'name': name,
    'version': '2.0.9',
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
    'long_description': open('smoker/DESCRIPTION.md').read(),
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
    'test_suite': 'tests',
    'package_data': {'smoker': ['DESCRIPTION.md']}
}

setup(**params)
