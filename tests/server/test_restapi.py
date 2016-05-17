#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

import copy
import datetime
import os
import pytest
from smoker.server.daemon import Smokerd
from smoker.server import exceptions as smoker_exceptions
import smoker.server.plugins as server_plugins
from smoker.server import restserver
import time


class TestRestAPI(object):
    """Unit tests for the restserver functions"""
    component_result = {
        'componentResults': {
            'Unit tests': {
                'status': 'OK',
                'messages': {
                    'info': ['GoodData'],
                    'warn': [],
                    'error': []
                }
            }
        }
    }
    conf_plugins = {
        'Uptime     ': {
            'Category': 'monitoring',
            'Command': 'uptime'},
        'Uname': {
            'Category': 'system',
            'Module': 'smoker.server.plugins.uname'},
        'Hostname': {
            'Category': 'system',
            'Command': 'hostname'}
    }
    conf_templates = {
        'BasePlugin': {
            'Interval': 1,
            'gid': 'default',
            'uid': 'default',
            'Timeout': 30,
            'History': 10}
    }
    config = {
        'plugins': conf_plugins,
        'templates': conf_templates,
        'actions': dict()}
    conf_dir = (os.path.dirname(os.path.realpath(__file__)) +
                '/smoker_test_resources/smokerd')
    smokerd = Smokerd(config=conf_dir + '/smokerd.yaml')
    # Map smokerd.pluginmgr to PluginManager instance
    # because we don't 'run' smokerd instance (work arround)
    smokerd.pluginmgr = server_plugins.PluginManager(**config)
    restserver.smokerd = smokerd

    def test_next_run_iso_format_boolean_input(self):
        assert restserver.next_run_iso_format(True) is None

    def test_next_run_iso_format_time_input(self):
        sample = datetime.datetime.now()
        next_run = restserver.next_run_iso_format(sample)
        assert next_run
        assert next_run == sample.isoformat()
        assert isinstance(next_run, str)

    def test_standardized_api_list_null_input(self):
        assert not restserver.standardized_api_list(None)

    def test_standardized_api_list_invalid_type_input(self):
        component_result = ['component', 'InvalidInput']
        result = restserver.standardized_api_list(component_result)
        assert result
        assert result == component_result
        assert isinstance(result, list)

    def test_standardized_api_list_missing_componentResults_keyword(self):
        component_result = {
            'InvalidKeyword': 'Smoker'
        }
        result = restserver.standardized_api_list(component_result)
        assert result
        assert result == component_result
        assert isinstance(result, dict)

    def test_standardized_api_list_valid_input(self):
        expected = {
            'componentResults': [
                {
                    'componentResult': {
                        'status': 'OK',
                        'messages': {
                            'info': ['GoodData'],
                            'warn': [],
                            'error': []
                        },
                        'name': 'Unit tests'
                    }
                }
            ]
        }
        result = restserver.standardized_api_list(self.component_result)
        assert result
        assert result == expected
        assert isinstance(result, dict)

    def test_print_plugin(self):
        plugin_result = restserver.print_plugin('Uname')
        assert plugin_result['plugin']
        assert plugin_result['plugin']['name'] == 'Uname'
        assert plugin_result['plugin']['links']['self'] == '/plugins/Uname'
        assert plugin_result['plugin']['parameters']

    def test_print_plugin_with_invalid_plugin_name(self):
        with pytest.raises(smoker_exceptions.NoSuchPlugin) as exc_info:
            restserver.print_plugin('InvalidPluginName')
        assert 'Plugin InvalidPluginName not found' in exc_info.value

    def test_forced_print_plugin_without_forced_result(self):
        with pytest.raises(smoker_exceptions.InProgress):
            restserver.print_plugin('Uname', forced=True)

    def test_forced_print_plugin_with_forced_result(self):
        plugin = self.smokerd.pluginmgr.get_plugin('Uname')
        plugin.forced = True
        plugin.run()
        time.sleep(0.5)

        plugin_result = restserver.print_plugin('Uname', forced=True)
        assert plugin_result['plugin']
        assert plugin_result['plugin']['name'] == 'Uname'
        assert plugin_result['plugin']['links']['self'] == '/plugins/Uname'
        assert plugin_result['plugin']['parameters']
        assert plugin_result['plugin']['forcedResult']['status'] == 'OK'
        assert plugin_result['plugin']['forcedResult']['forced'] is True
        assert plugin_result['plugin']['forcedResult']['messages']['info']

    def test_print_plugins(self):
        plugins_to_print = self.conf_plugins.keys()
        plugins_result = restserver.print_plugins(plugins_to_print)
        assert plugins_result['plugins']
        assert len(plugins_result['plugins']['items']) == len(plugins_to_print)

        for plugin_name in plugins_to_print:
            index = plugins_to_print.index(plugin_name)
            plugin_result = plugins_result['plugins']['items'][index]['plugin']
            assert plugin_result['name'] == plugin_name
            assert plugin_result['links']['self'] == '/plugins/' + plugin_name
            assert plugin_result['parameters']

    def test_forced_print_plugins_with_forced_result(self):
        plugins_to_print = self.conf_plugins.keys()
        for plugin in self.smokerd.pluginmgr.get_plugins().values():
            plugin.forced = True
            plugin.run()
        time.sleep(0.5)
        plugins_result = restserver.print_plugins(plugins_to_print,
                                                  forced=True)
        assert plugins_result['plugins']
        assert len(plugins_result['plugins']['items']) == len(plugins_to_print)

        for plugin_name in plugins_to_print:
            index = plugins_to_print.index(plugin_name)
            plugin_result = plugins_result['plugins']['items'][index]['plugin']
            assert plugin_result['name'] == plugin_name
            assert plugin_result['links']['self'] == '/plugins/' + plugin_name
            assert plugin_result['parameters']
            assert plugin_result['forcedResult']['status'] == 'OK'
            assert plugin_result['forcedResult']['forced'] is True
            assert plugin_result['forcedResult']['messages']['info']

    def test_get_plugin_history(self):
        config = copy.deepcopy(self.config)
        smokerd = Smokerd(config=self.conf_dir + '/smokerd.yaml')
        smokerd.pluginmgr = server_plugins.PluginManager(**config)
        restserver.smokerd = smokerd

        plugin = smokerd.pluginmgr.get_plugin('Uname')
        for i in range(4):
            plugin.forced = True
            plugin.run()
            time.sleep(0.5)
            plugin.collect_new_result()
        plugin_history = restserver.get_plugin_history('Uname')
        assert len(plugin_history) == 4

    def test_reset_smokerd_instance(self):
        # To prevent data changed from test_get_plugin_history in smokerd
        config = copy.deepcopy(self.config)
        self.smokerd = Smokerd(config=self.conf_dir + '/smokerd.yaml')
        self.smokerd.pluginmgr = server_plugins.PluginManager(**config)
        restserver.smokerd = self.smokerd
