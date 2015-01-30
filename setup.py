#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import os
import sys
from setuptools import setup

CONFIGDIR = '/etc/smokerd'
INITDIR = '/etc/rc.d/init.d'

# Parameters for build
params = {
    # This package is named gdc-smoker on Pypi, use it on register or upload actions
    'name' : 'gdc-smoker' if 'upload' in sys.argv or 'register' in sys.argv else 'smoker',
    'version' : '1.0.4',
    'packages' : [
        'smoker',
        'smoker.server',
        'smoker.server.plugins',
        'smoker.client',
        'smoker.client.out_junit',
        'smoker.client.plugins',
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
    'long_description' : """About
-------
Smoker (aka Smoke Testing Framework) is a framework for distributed execution of Python modules, shell commands or external tools.
It executes configured plugins on request or periodically, unifies output and provide it via REST API for it's command-line or other client.

Also it's free software, licensed under the terms of BSD license - feel free to contribute!

Purpose and use
---------------
It was developed in GoodData to satisfy single use-case - be able to quickly and easily check that all services and components are functional overall cluster.
That may be simple if you have similar services with unified communication protocols. But if you have many services and components, written in many languages including Java, Perl, Erlang, Python together, you need more customizable approach, because each language has it's specific way to test things.

For example.. if you have services written in Java, you may use JMX interface to execute test function and get result.
For services with REST API, you may want to call it's API to get the result.
And of course you want to test system services. For example check Varnish backends health by executing `varnishadm 'debug.health'`. Or checking that Mongo is configured correctly by running custom Python plugin or shell script.

All those tests will return something different - you may get JSON response from REST API, XML from Java service, more complex data structure from Python plugin or simple STDOUT/STDERR and exit value from shell script. Smoker server will unify all those outputs and serve results over REST API so you can connect via CLI client and find out what is wrong in your cluster.

These tests may be executed periodically or when requested by client.
And actions are supported as well - you can write your own action plugin, parse result, decide and execute some action. For example, you can send status via NSCA to your Nagios system. Or you can just restart service when it's not working.

But Smoker can do more - you can use it if you want to execute any job and see it's result in a readable way. For some purposes, it may be more suitable than Cron.

Common use-cases in short:
 * execute smoke tests on newly deployed systems
 * execute checks periodically, send output to monitoring system (eg. Nagios)
 * execute jobs that requires attention on result or output (like Cron with ability to store results)""",
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
    'provides' : ['smoker'],
    'install_requires' : ['PyYAML', 'argparse', 'simplejson', 'psutil', 'setproctitle', 'Flask-RESTful'],
    'data_files': [
        (INITDIR, ['rc.d/init.d/smokerd']),
        (CONFIGDIR, ['etc/smokerd-example.yaml', 'etc/smokercli-example.yaml'])
    ]
}

# Get current branch
branch = os.getenv('GIT_BRANCH')
if not branch:
    branch = os.popen(
        'git branch|grep -v "no branch"|grep \*|sed s,\*\ ,,g').read().strip()

    if not branch:
        branch = 'master'
else:
    branch = branch.replace('origin/', '')

# Get git revision hash
revision = os.popen('git rev-parse --short HEAD').read().strip()

if not revision:
    revision = '0'

# Get build number
build = os.getenv('BUILD_NUMBER')
if not build:
    build = '1'

try:
    action = sys.argv[1]
except IndexError:
    action = None

if action == 'clean':
    # Remove MANIFEST file
    print "Cleaning MANIFEST.."
    try:
        os.unlink('MANIFEST')
    except OSError as e:
        if e.errno == 2:
            pass
        else:
            raise

    # Remove dist and build directories
    for dir in ['dist', 'build']:
        print "Cleaning %s.." % dir
        for root, dirs, files in os.walk(dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        try:
            os.rmdir(dir)
        except OSError as e:
            if e.errno == 2:
                pass
            else:
                raise
elif action == 'bdist_rpm':
    # Set release number
    sys.argv.append('--release=1.%s.%s' % (build, revision))
    # Require same version of gdc-python-common package
    sys.argv.append(
        '--requires=python-argparse python-simplejson python-setproctitle '
        'python-flask-restful')

setup(**params)
