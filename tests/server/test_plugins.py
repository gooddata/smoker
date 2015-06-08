#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

from multiprocessing import Queue
from smoker.server.plugins import PluginManager, Plugin, PluginWorker
import unittest
import time


class TestPluginManager(unittest.TestCase):
    """
    Unit tests for the PluginManager class
    """
    def test_example_config(self):
        config = {}
        config['plugins'] = {
            'Uptime': {
                'Category': 'system',
                'Enabled': True,
                'Interval': 5,
                'Command': 'uptime',
                'Timeout': 5},
            'Uname': {
                'Category': 'system',
                'Interval': 30,
                'Enabled': True,
                'Module': 'smoker.server.plugins.uname'},
            'Memory': {
                'Category': 'system',
                'Enabled': True,
                'Interval': 180,
                'Command': 'echo "$(top -l 1 | awk \'/PhysMem/\';)"',
                'Timeout': 5},
        }
        config['templates'] = {
            'BasePlugin': {
                'Interval': 5,
                'gid': 'default',
                'uid': 'default',
                'Timeout': 30,
                'History': 10}
        }
        config['actions'] = {}

        PluginManager(**config)


class TestPlugin(unittest.TestCase):
    """
    Unit tests for the Plugin class
    """
    def test_plugin_uptime(self):
        options = {
            'Category': 'system',
            'Enabled': True,
            'Interval': 5,
            'Command': 'uptime',
            'Timeout': 5
        }

        foo = Plugin('unittest', options)
        foo.forced = True
        foo.run()
        time.sleep(0.5)
        foo.collect_new_result()


class TestPluginWorker(unittest.TestCase):
    """
    Unit tests for the PluginWorker class
    """
    def test_plugin_worker_uptime(self):
        queue = Queue()
        params = {
            'Category': 'system',
            'Parser': None,
            'uid': 'default',
            'Interval': 5,
            'Enabled': True,
            'Module': None,
            'gid': 'default',
            'Command': 'uptime',
            'Timeout': 5,
            'Action': None,
            'Template': None,
            'History': 10
        }

        worker = PluginWorker('test', queue, params)
        worker.start()
        result = queue.get()
        worker.join()
        self.assertNotEqual(result, None)
