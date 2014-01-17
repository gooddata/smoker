#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

from setuptools import setup

# Parameters for build
params = {
    'name' : 'gdc-smoker',
    'version' : '1.0',
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
    'license' : 'BSD',
    'author' : 'GoodData Corporation',
    'author_email' : 'python@gooddata.com',
    'description' : 'GDC Smoker',
    'long_description' : 'GoodData Smoke testing daemon and client',
    'requires' : ['yaml', 'argparse', 'simplejson', 'psutil'],
}

setup(**params)
