#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import sys
from setuptools import setup

# Parameters for build
params = {
    # This package is named gdc-smoker on Pypi, use it on register or upload actions
    'name' : 'gdc-smoker' if len(sys.argv) > 1 and sys.argv[1] in ['register', 'upload'] else 'smoker',
    'version' : '1.0.1',
    'packages' : [
        'smoker',
        'smoker.server',
        'smoker.server.plugins',
        'smoker.client',
        'smoker.logger',
        'smoker.util'
        ],
    'scripts' : [
        'bin/smokerd.py',
        'bin/smokercli.py',
        'bin/check_smoker_plugin.py',
        ],
    'url' : 'https://github.com/gooddata/smoker',
    'download_url' : 'https://github.com/gooddata/smoker',
    'license' : 'BSD',
    'author' : 'GoodData Corporation',
    'author_email' : 'python@gooddata.com',
    'maintainer' : 'Filip Pytloun',
    'maintainer_email' : 'filip@pytloun.cz',
    'description' : 'Smoke Testing Framework',
    'long_description' : "Smoker is framework for distributed execution of Python modules, shell commands or external tools. It executes configured plugins on request or periodically, unifies output and provide it via REST API for it's command-line or other client.",
    'classifiers' : [
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
    'platforms' : ['POSIX'],
    'provides' : 'smoker',
    'requires' : ['yaml', 'argparse', 'simplejson', 'psutil'],
}

setup(**params)
