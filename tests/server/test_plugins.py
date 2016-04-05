#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

import copy
import datetime
import lockfile
import multiprocessing
import os
import psutil
import pytest
import re
from smoker.server import exceptions as smoker_exceptions
import smoker.server.plugins as server_plugins
import time


class TestPluginManager(object):
    """Unit tests for the PluginManager class"""

    conf_plugins_to_load = {
        'CpuLoad': {
            'Category': 'monitoring',
            'Enabled': True,
            'Command': 'top',
            'Template': 'SystemPlugin'},
        'Uname': {
            'Category': 'system',
            'Interval': 5,
            'Module': 'smoker.server.plugins.uname'},
        'Hostname': {
            'Category': 'system',
            'Command': 'hostname',
            'Action': 'GetFQDN'}
    }
    conf_plugins_with_enabled_is_false = {
        'Memory': {
            'Category': 'system',
            'Enabled': False,
            'Interval': 15,
            'Command': 'echo "$(top -l 1 | awk \'/PhysMem/\';)"',
            'Timeout': 5}
    }
    conf_plugins_with_template_is_false = {
        'Uptime': {
            'Category': 'system',
            'Enabled': True,
            'Interval': 5,
            'Command': 'uptime',
            'Timeout': 5,
            'Template': 'InvalidTemplate'}
    }
    conf_plugins = dict(
        conf_plugins_to_load.items() +
        conf_plugins_with_enabled_is_false.items() +
        conf_plugins_with_template_is_false.items())

    conf_templates = {
        'BasePlugin': {
            'Interval': 2,
            'gid': 'default',
            'uid': 'default',
            'Timeout': 30,
            'History': 10},
        'SystemPlugin': {
            'Interval': 3,
            'Timeout': 5}
    }
    conf_actions = {
        'GetFQDN': {
            'Command': 'hostname -f'}
    }
    config = {
        'plugins': conf_plugins,
        'templates': conf_templates,
        'actions': conf_actions}
    # Due to 'load_plugin' will override 'conf_actions', please deepcopy
    # 'conf_actions' or whole 'config' before using.
    # It'll be fixed if any issue affect smoker itself

    pluginmgr = server_plugins.PluginManager(**copy.deepcopy(config))
    loaded_plugins = pluginmgr.get_plugins()

    def test_disabled_plugins_should_not_be_loaded(self):
        plugins = self.conf_plugins_with_template_is_false.iteritems()
        for plugin, options in plugins:
            if 'Enabled' in options and not options['Enabled']:
                assert plugin not in self.loaded_plugins.keys()

    def test_enabled_plugins_should_be_loaded(self):
        for plugin, options in self.conf_plugins_to_load.iteritems():
            if 'Enabled' in options and options['Enabled']:
                assert plugin in self.loaded_plugins.keys()

    def test_plugins_without_enabled_option_should_be_loaded(self):
        for plugin, options in self.conf_plugins_to_load.iteritems():
            if 'Enabled' not in options:
                assert plugin in self.loaded_plugins.keys()

    def test_plugins_are_rightly_loaded(self):
        assert len(self.loaded_plugins) == len(self.conf_plugins_to_load)

    def test_plugins_not_in_config_should_not_be_loaded(self):
        for plugin in self.loaded_plugins:
            assert plugin in self.conf_plugins

    def test_load_plugins_without_baseplugin_template_will_get_error(self):
        templates = {
            'SmokerPlugin': {
                'Interval': 5,
                'gid': 'default',
                'uid': 'default',
                'Timeout': 30,
                'History': 10}
        }
        actions = copy.deepcopy(self.conf_actions)
        with pytest.raises(smoker_exceptions.BasePluginTemplateNotFound):
            server_plugins.PluginManager(plugins=self.conf_plugins,
                                         templates=templates,
                                         actions=actions)

    def test_no_plugin_to_load(self):
        actions = copy.deepcopy(self.conf_actions)
        with pytest.raises(smoker_exceptions.NoRunningPlugins) as exc_info:
            server_plugins.PluginManager(plugins=dict(),
                                         templates=self.conf_templates,
                                         actions=actions)
        assert 'No plugins loaded!' in exc_info.value

    def test_load_plugins_without_any_template(self):
        actions = copy.deepcopy(self.conf_actions)
        with pytest.raises(smoker_exceptions.BasePluginTemplateNotFound):
            server_plugins.PluginManager(plugins=self.conf_plugins,
                                         templates=dict(),
                                         actions=actions)

    def test_load_plugins_with_template_is_true(self):
        # Plugin has template and template is in conf_template
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        for plugin in self.conf_plugins_to_load:
            if 'Template' in self.conf_plugins_to_load[plugin]:
                assert plugin in pluginmgr.get_plugins()
                assert 'Template' in pluginmgr.get_plugin(plugin).params
                templates = pluginmgr.get_plugin(plugin).params['Template']
                assert 'SystemPlugin' in templates

    def test_load_plugins_with_template_is_false(self):
        # Plugin has template and template is in conf_template
        templates = {
            'BasePlugin': {
                'Interval': 5,
                'gid': 'default',
                'uid': 'default',
                'Timeout': 30,
                'History': 10}
        }
        conf = dict(copy.deepcopy(self.config), **{'templates': templates})
        pluginmgr = server_plugins.PluginManager(**conf)
        for plugin in self.conf_plugins_to_load:
            if 'Template' in self.conf_plugins_to_load[plugin]:
                assert plugin not in pluginmgr.get_plugins()

    def test_load_plugins_with_actions(self):
        expected = {
            'Command': 'hostname -f',
            'Module': None,
            'Timeout': 60
        }
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        action = pluginmgr.plugins['Hostname'].params['Action']
        assert action == expected

    def test_load_plugins_with_blank_actions(self):
        actions = {
            'GetFQDN': dict()
        }
        conf = dict(copy.deepcopy(self.config), **{'actions': actions})
        pluginmgr = server_plugins.PluginManager(**conf)
        assert not pluginmgr.plugins['Hostname'].params['Action']

    def test_plugins_without_params_will_use_params_from_base_plugin(self):
        expected_interval = self.conf_templates['BasePlugin']['Interval']
        for plugin_name, plugin in self.conf_plugins_to_load.iteritems():
            if not plugin.get('Interval') and not plugin.get('Template'):
                assert (self.loaded_plugins[plugin_name].params['Interval'] ==
                        expected_interval)

    def test_get_plugins_with_filter(self):
        filter_ = {'Category': 'system'}
        expected_plugins = ['Uname', 'Hostname']
        load_plugins_with_filter = self.pluginmgr.get_plugins(filter=filter_)

        assert len(expected_plugins) == len(load_plugins_with_filter)
        for plugin in load_plugins_with_filter:
            assert plugin.name in expected_plugins

    def test_get_plugins_with_invalid_name(self):
        with pytest.raises(smoker_exceptions.NoSuchPlugin) as exc_info:
            self.pluginmgr.get_plugin('InvalidPlugin')
        assert 'Plugin InvalidPlugin not found' in exc_info.value

    def test_get_non_exist_template(self):
        with pytest.raises(smoker_exceptions.TemplateNotFound) as exc_info:
            self.pluginmgr.get_template('InvalidTemplate')
        expected = 'Can\'t find configured template InvalidTemplate'
        assert expected in exc_info.value

    def test_get_template(self):
        assert (self.pluginmgr.get_template('BasePlugin') ==
                self.conf_templates['BasePlugin'])

    def test_add_process_using_plugin_list(self):
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))

        plugin_list = ['Uname', 'CpuLoad']
        expected_plugins = list()
        for plugin in plugin_list:
            expected_plugins.append(pluginmgr.get_plugin(plugin))

        process_id = pluginmgr.add_process(plugins=plugin_list)
        added_process = pluginmgr.get_process_list()[process_id]['plugins']
        assert expected_plugins == added_process

    def test_add_process_using_filter(self):
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        filter_ = {'Category': 'system'}
        expected_plugins = pluginmgr.get_plugins(filter=filter_)

        process_id = pluginmgr.add_process(filter=filter_)
        added_process = pluginmgr.get_process_list()[process_id]['plugins']
        assert expected_plugins == added_process

    def test_add_process_using_plugin_list_and_filter(self):
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        plugin_list = ['Uname', 'CpuLoad']
        filter_ = {'Category': 'system'}

        # Plugins from list will be added to process first,
        # then plugins from filter
        expected_plugins = list()
        for plugin in plugin_list:
            expected_plugins.append(pluginmgr.get_plugin(plugin))
        expected_plugins += pluginmgr.get_plugins(filter=filter_)

        process_id = pluginmgr.add_process(plugins=plugin_list, filter=filter_)
        added_process = pluginmgr.get_process_list()[process_id]['plugins']
        assert expected_plugins == added_process

    def test_add_process_without_any_plugin(self):
        conf = copy.deepcopy(self.config)
        with pytest.raises(smoker_exceptions.NoPluginsFound):
            server_plugins.PluginManager(**conf).add_process()

    def test_add_process_with_invalid_plugin_name(self):
        conf = copy.deepcopy(self.config)
        with pytest.raises(smoker_exceptions.NoSuchPlugin) as exc_info:
            pluginmgr = server_plugins.PluginManager(**conf)
            pluginmgr.add_process(plugins=['InvalidPlugin'])
        assert 'Plugin InvalidPlugin not found' in exc_info.value

    def test_get_process_with_invalid_process_id(self):
        with pytest.raises(IndexError):
            self.pluginmgr.get_process(9999)
        # Should equal None
        assert not self.pluginmgr.get_process(0)

    def test_run_plugins_with_interval(self):
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        time.sleep(5.5)
        pluginmgr.run_plugins_with_interval()
        for plugin in pluginmgr.plugins.values():
            assert plugin.current_run

    def test_get_action(self):
        assert (self.pluginmgr.get_action('GetFQDN') ==
                self.conf_actions['GetFQDN'])

    def test_get_non_exist_action(self):
        with pytest.raises(smoker_exceptions.ActionNotFound) as exc_info:
            self.pluginmgr.get_action('InvalidAction')
        expected = 'Can\'t find configured action InvalidAction'
        assert expected in exc_info.value

    def test_join_timed_plugin_workers(self):
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        plugin = pluginmgr.get_plugin('Hostname')
        time.sleep(plugin.params['Interval'] + 0.5)
        plugin.run()
        time.sleep(0.5)
        assert plugin.current_run

        pluginmgr.join_timed_plugin_workers()
        assert not plugin.current_run

    def test_join_non_timed_plugin_workers(self):
        # Schedule and run plugin (Plugin require 'Interval' to run)
        pluginmgr = server_plugins.PluginManager(**copy.deepcopy(self.config))
        plugin = pluginmgr.get_plugin('Hostname')
        time.sleep(plugin.params['Interval'] + 0.5)
        plugin.run()
        time.sleep(0.5)
        assert plugin.current_run

        plugin.params['Interval'] = 0
        pluginmgr.join_timed_plugin_workers()
        assert plugin.current_run


class TestPlugin(object):
    """Unit tests for the Plugin class"""

    test_params_default = {
        'Command': 'hostname -f',
        'Module': None,
        'Parser': None,
        'Timeout': 180,
    }
    test_plugin_name = 'hostname'
    plugin = server_plugins.Plugin(name=test_plugin_name,
                                   params=test_params_default)

    def test_create_plugin_test_params_default(self):
        expected_params = {
            'Command': 'hostname -f',
            'Module': None,
            'Parser': None,
            'Interval': 0,
            'Timeout': 180,
            'History': 10,
            'uid': 'default',
            'gid': 'default',
            'Template': None,
            'Action': None,
            'MaintenanceLock': None
        }
        assert self.plugin.params == expected_params

    def test_validate_created_plugin(self):
        with pytest.raises(smoker_exceptions.InvalidConfiguration) as exc_info:
            params = dict(self.test_params_default, **{'Timeout': 0})
            server_plugins.Plugin(name=self.test_plugin_name, params=params)
        assert 'Timeout parameter can\'t be 0' in exc_info.value

        with pytest.raises(smoker_exceptions.InvalidConfiguration) as exc_info:
            params = dict(self.test_params_default, **{'Command': None})
            server_plugins.Plugin(name=self.test_plugin_name, params=params)
        assert 'Command or Module parameter has to be set' in exc_info.value

        with pytest.raises(smoker_exceptions.InvalidConfiguration) as exc_info:
            test_params = {
                'Command': 'hostname -f',
                'Module': 'server_plugins.hostname'
            }
            params = dict(self.test_params_default, **test_params)
            server_plugins.Plugin(name=self.test_plugin_name, params=params)
        expected = 'Command and Module parameters cannot be set together'
        assert expected in exc_info.value

        with pytest.raises(smoker_exceptions.InvalidConfiguration) as exc_info:
            test_params = {
                'Command': None,
                'Parser': 'server_plugins.hostnameparser',
                'Module': 'server_plugins.hostname'
            }
            params = dict(self.test_params_default, **test_params)
            server_plugins.Plugin(name=self.test_plugin_name, params=params)
        expected = 'Parser can be used only with Command parameter'
        assert expected in exc_info.value

    def test_schedule_run_with_time(self):
        next_run = (datetime.datetime.now() + datetime.timedelta(seconds=3))
        self.plugin.schedule_run(time=next_run)
        assert self.plugin.next_run == next_run

    def test_schedule_run_with_invalid_time_format(self):
        with pytest.raises(smoker_exceptions.InvalidArgument) as exc_info:
            self.plugin.schedule_run(time=15)
        expected = 'Parameter time has to be an instance of datetime object'
        assert expected in exc_info.value

        with pytest.raises(smoker_exceptions.InvalidArgument) as exc_info:
            self.plugin.schedule_run(time=time.ctime())
        expected = 'Parameter time has to be an instance of datetime object'
        assert expected in exc_info.value

    def test_schedule_run_now(self):
        self.plugin.schedule_run(now=True)
        delta = (datetime.datetime.now() - self.plugin.next_run)
        assert round(delta.total_seconds(), 0) == 0

    def test_schedule_run_with_interval(self):
        params = dict(self.test_params_default, **{'Interval': 15})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)

        delta = (plugin.next_run - datetime.datetime.now())
        assert round(delta.total_seconds(), 0) == plugin.params['Interval']

    def test_force_to_run_plugin_without_interval_parameter(self):
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=self.test_params_default)
        plugin.forced = True
        plugin.run()
        time.sleep(0.5)
        assert plugin.current_run
        assert type(plugin.current_run).__name__ == 'PluginWorker'
        assert not plugin.next_run
        assert plugin.forced

    def test_force_to_run_plugin_with_interval_parameter(self):
        # should not schedule next_run
        params = dict(self.test_params_default, **{'Interval': 2})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)
        n = plugin.next_run
        plugin.forced = True

        plugin.run()
        time.sleep(0.5)
        assert plugin.current_run
        assert type(plugin.current_run).__name__ == 'PluginWorker'
        assert n == plugin.next_run
        assert plugin.forced

    def test_run_plugin_with_interval(self):
        params = dict(self.test_params_default, **{'Interval': 2})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)
        time.sleep(2.5)
        assert not plugin.current_run
        plugin.run()
        time.sleep(0.5)
        assert plugin.current_run
        assert type(plugin.current_run).__name__ == 'PluginWorker'

    def test_run_plugin_with_interval_should_schedule_next_run(self):
        params = dict(self.test_params_default, **{'Interval': 2})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)
        time.sleep(2.5)
        plugin.run()
        delta = (plugin.next_run - datetime.datetime.now())
        assert round(delta.total_seconds(), 0) == plugin.params['Interval']

    def test_plugin_should_not_be_run_without_interval_parameter(self):
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=self.test_params_default)
        assert not plugin.next_run
        plugin.forced = False
        plugin.run()
        time.sleep(0.5)
        assert not plugin.current_run

    def test_interval_run_plugin_and_collect_new_result(self):
        params = dict(self.test_params_default, **{'Interval': 2})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)
        time.sleep(2.5)
        plugin.run()
        time.sleep(0.5)

        assert not plugin.get_last_result()
        plugin.collect_new_result()
        result = plugin.get_last_result()
        assert 'status' in result and result['status'] == 'OK'
        assert 'forced' in result and not result['forced']

    def test_force_plugin_to_run_and_collect_new_result(self):
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=self.test_params_default)
        plugin.forced = True
        plugin.run()
        time.sleep(0.5)
        assert not plugin.get_last_result()
        plugin.collect_new_result()
        # plugin.force should switch to False after result is collected
        assert not plugin.forced
        result = plugin.forced_result
        assert 'status' in result and result['status'] == 'OK'
        assert 'forced' in result and result['forced']

    def test_history_of_collect_new_result(self):
        params = dict(self.test_params_default, **{'History': 5})
        plugin = server_plugins.Plugin(name=self.test_plugin_name,
                                       params=params)
        for n in range(7):
            plugin.forced = True
            plugin.run()
            time.sleep(0.5)
            plugin.collect_new_result()

        assert len(plugin.result) == params['History']
        assert plugin.forced_result == plugin.result[-1]


class TestPluginWorker(object):
    """Unit tests for the PluginWorker class"""
    action = {
        'Command': 'hostname -f',
        'Module': None,
        'Timeout': 60
    }
    params_default = {
        'Command': 'hostname',
        'Module': None,
        'Parser': None,
        'uid': 'default',
        'gid': 'default',
        'MaintenanceLock': None,
        'Timeout': 30,
        'Action': None
    }
    queue = multiprocessing.Queue()

    conf_worker = {
        'name': 'Hostname',
        'queue': queue,
        'params': params_default,
        'forced': False
    }

    def test_running_worker_process(self):
        worker = server_plugins.PluginWorker(**self.conf_worker)
        worker.run()
        assert 'status' in worker.result and worker.result['status'] == 'OK'
        assert 'info' in worker.result['messages']
        assert worker.result['messages']['info'] == [os.uname()[1]]

    def test_running_worker_process_title_should_be_changed(self):
        expected = 'smokerd plugin Hostname'
        worker = server_plugins.PluginWorker(**self.conf_worker)
        worker.run()
        procs = get_process_list()
        assert expected in procs.values()

    def test_drop_privileged_with_invalid_params(self):
        test_params = {
            'uid': 99999,
            'gid': 99999
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)
        with pytest.raises(OSError) as exc_info:
            worker.run()
        assert 'Operation not permitted' in exc_info.value

    def test_drop_privileged_with_invalid_params_type(self):
        test_params = {
            'uid': 'InvalidType',
            'gid': 'InvalidType',
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)
        with pytest.raises(TypeError) as exc_info:
            worker.run()
        assert 'an integer is required' in exc_info.value

    def test_run_worker_with_maintenance_lock(self):
        expected_message = ['Skipped because of maintenance in progress']

        maintenance_lock = os.getcwd() + random_string()
        test_params = {'MaintenanceLock': maintenance_lock + '.lock'}
        params = dict(self.params_default, **test_params)
        lock = lockfile.FileLock(maintenance_lock)
        with lock:
            worker = server_plugins.PluginWorker(name='Hostname',
                                                 queue=self.queue,
                                                 params=params)
            worker.run()
            assert 'status' in worker.result
            assert worker.result['status'] == 'WARN'
            assert 'warn' in worker.result['messages']
            assert worker.result['messages']['warn'] == expected_message

    def test_run_invalid_command(self):
        expected = 'InvalidCommand|command not found'
        test_params = {
            'Command': 'InvalidCommand'
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='InvalidCommand',
                                             queue=self.queue, params=params)
        worker.run()
        assert 'status' in worker.result and worker.result['status'] == 'ERROR'
        assert 'warn' in worker.result['messages']
        assert re.search(expected, worker.result['messages']['error'][0])

    def test_run_command_with_parser(self):
        expected = {
            'Unit tests': {
                'status': 'OK',
                'messages': {
                    'info': ['GoodData'],
                    'warn': [],
                    'error': []
                }
            }
        }
        test_params = {
            'Command': 'echo "GoodData Smoker"',
            'Parser': 'tests.server.smoker_test_resources.smokerparser'
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)
        worker.run()
        assert 'status' in worker.result and worker.result['status'] == 'OK'
        assert 'componentResults' in worker.result
        assert worker.result['componentResults'] == expected
        assert 'messages' in worker.result and not worker.result['messages']

    def test_run_command_with_invalid_parser_path(self):
        expected_info = ['GoodData Smoker']
        expected_error = ['Parser run failed: No module named InvalidParser']
        test_params = {
            'Command': 'echo "GoodData Smoker"',
            'Parser': 'InvalidParser'
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)
        worker.run()
        assert 'status' in worker.result and worker.result['status'] == 'ERROR'
        assert 'info' and 'error' in worker.result['messages']
        assert worker.result['messages']['info'] == expected_info
        assert worker.result['messages']['error'] == expected_error

    def test_run_parser(self):
        expected = {
            'Unit tests': {
                'status': 'OK',
                'messages': {
                    'info': ['GoodData'],
                    'warn': [],
                    'error': []
                }
            }
        }
        test_params = {
            'Command': 'echo "Output : GoodData Smoker"',
            'Parser': 'tests.server.smoker_test_resources.smokerparser'
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)
        result = worker.run_parser(stdout='GoodData', stderr='').result

        assert 'status' in result and result['status'] == 'OK'
        assert result['componentResults'] == expected
        assert 'messages' in result and not result['messages']
        assert (result['componentResults']['Unit tests']['status'] ==
                result['status'])

    def test_run_invalid_parser(self):
        test_params = {
            'Command': 'echo "Output : GoodData Smoker"',
            'Parser': 'InvalidParser'
        }
        params = dict(self.params_default, **test_params)
        worker = server_plugins.PluginWorker(name='Hostname',
                                             queue=self.queue, params=params)

        with pytest.raises(ImportError) as exc_info:
            worker.run_parser(stdout='GoodData', stderr='')
        assert 'No module named InvalidParser' in exc_info.value

    def test_run_module(self):
        worker = server_plugins.PluginWorker(**self.conf_worker)
        module = 'tests.server.smoker_test_resources.smokermodule'
        result = worker.run_module(module).result
        assert 'status' in result and result['status'] == 'OK'
        assert 'info' in result['messages']
        assert result['messages']['info'] == [' '.join(os.uname())]

    def test_run_invalid_module(self):
        worker = server_plugins.PluginWorker(**self.conf_worker)
        module = 'InvalidModule'
        with pytest.raises(ImportError) as exc_info:
            worker.run_module(module)
        assert 'No module named InvalidModule' in exc_info.value

    def test_escape(self):
        worker = server_plugins.PluginWorker(**self.conf_worker)

        tbe_str = 'string \ '
        assert worker.escape(tbe=tbe_str) == re.escape(tbe_str)

        tbe_dict = {'dict': '\ "" '}
        expected_dict = {'dict': '\\\\\\ \\"\\"\\ '}
        assert worker.escape(tbe=tbe_dict) == expected_dict

        tbe_list = [1, '[Good]Data', '/\G']
        expected_list = [1, '\\[Good\\]Data', '\\/\\\\G']
        assert worker.escape(tbe=tbe_list) == expected_list

        tbe_tuple = {1, '[Good]Data', '/\G'}
        with pytest.raises(Exception) as exc_info:
            worker.escape(tbe=tbe_tuple)
        assert 'Unknown data type' in exc_info.value

    def test_get_params(self):
        worker = server_plugins.PluginWorker(**self.conf_worker)
        assert worker.get_param('Command') == 'hostname'
        assert worker.get_param('Timeout') == 30
        assert not worker.get_param('MaintenanceLock')
        assert not worker.get_param('InvalidParamater')


class TestResult(object):
    """Unit tests for the PluginWorker class"""

    result_to_validate = {
        'status': 'OK',
        'messages': {
            'info': [],
            'warn': [],
            'error': []
        },
        'lastRun': datetime.datetime.now().isoformat(),
        'componentResults': None,
        'action': None,
        'forced': False
    }

    def test_set_status(self):
        result = server_plugins.Result()
        result.set_status('OK')
        assert result.result['status'] == 'OK'
        result.set_status('ERROR')
        assert result.result['status'] == 'ERROR'
        result.set_status('WARN')
        assert result.result['status'] == 'WARN'

        for status in ['OK', 'WARN', 'ERROR']:
            component_results = {
                'Unit tests': {
                    'status': status,
                    'messages': {
                        'info': ['GoodData'],
                        'warn': [],
                        'error': []
                    }
                }
            }
            result = server_plugins.Result()
            result.result['componentResults'] = component_results
            result.set_status()
            assert status == result.result['status']

    def test_set_invalid_status(self):
        result = server_plugins.Result()
        expected = 'Can\'t generate overall status without component results'
        with pytest.raises(Exception) as exc_info:
            result.set_status()
        assert expected in exc_info.value

        expected = 'Status has to be OK, ERROR or WARN'
        with pytest.raises(smoker_exceptions.InvalidArgument) as exc_info:
            result.set_status('InvalidStatus')
        assert expected in exc_info.value

    def test_add_msg(self):
        for level in ['info', 'warn', 'error']:
            result = server_plugins.Result()
            result.add_msg(level, 'Gooddata')
            result.add_msg(level, 'Smoker')
            result.add_msg(level, level)
            expected_info = ['Gooddata', 'Smoker', level]
            assert 'status' in result.result and not result.result['status']
            assert level in result.result['messages']
            assert expected_info == result.result['messages'][level]

    def test_add_msg_with_invalid_level(self):
        result = server_plugins.Result()
        with pytest.raises(smoker_exceptions.InvalidArgument) as exc_info:
            result.add_msg('InvalidLevel', 'Gooddata')
        assert 'Level has to be info, error or warn' in exc_info.value

    def test_add_msg_with_multiline_is_true(self):
        for level in ['info', 'warn', 'error']:
            result = server_plugins.Result()
            result.add_msg(level, 'Gooddata\nSmoker', multiline=True)
            result.add_msg(level, level)
            expected_info = ['Gooddata\nSmoker', level]
            assert 'status' in result.result and not result.result['status']
            assert level in result.result['messages']
            assert expected_info == result.result['messages'][level]

    def test_add_msg_with_multiline_is_false(self):
        for level in ['info', 'warn', 'error']:
            result = server_plugins.Result()
            result.add_msg(level, 'Gooddata\nSmoker')
            result.add_msg(level, level)
            expected_info = ['Gooddata', 'Smoker', level]
            assert 'status' in result.result and not result.result['status']
            assert level in result.result['messages']
            assert expected_info == result.result['messages'][level]

    def test_validate_status(self):
        for status in ['OK', 'ERROR', 'WARN']:
            result = server_plugins.Result()
            result.result = copy.deepcopy(self.result_to_validate)
            result.result['status'] = status
            result.validate()
            assert result.validated

    def test_validate_invalid_status(self):
        expected = 'Result status has to be OK, ERROR or WARN, ' \
                   'not InvalidStatus'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['status'] = 'InvalidStatus'
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_message_should_be_dict(self):
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['messages'] = str()
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        expected = 'Result message has to be a dictionary or None, not str'
        assert expected in exc_info.value

    def test_validate_level_message_should_be_list(self):
        for level in ['info', 'error', 'warn']:
            result = server_plugins.Result()
            result.result = copy.deepcopy(self.result_to_validate)
            result.result['messages'][level] = str()
            with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
                result.validate()
            expected = 'Can\'t validate message: Result message type %s has ' \
                       'to be a list, not str' % level
            assert expected in exc_info.value

    def test_validate_level_message_output_should_be_string(self):
        for level in ['info', 'error', 'warn']:
            result = server_plugins.Result()
            result.result = copy.deepcopy(self.result_to_validate)
            result.result['messages'][level] = ['Gooddata', ['Invalid_Data']]
            with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
                result.validate()
            expected = 'Can\'t validate message: Result message type %s has ' \
                       'to be a string, not list' % level
            assert expected in exc_info.value

    def test_validate_component_result_should_be_dict(self):
        expected = 'Component result must be dictionary'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['componentResults'] = list()
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_component_result_should_have_message(self):
        component_results = {
            'Unit tests': {
                'status': 'OK',
            }
        }
        expected = 'Component Unit tests doesn\'t have message'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['componentResults'] = component_results
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_component_result_should_have_status(self):
        component_results = {
            'Unit tests': {
                'messages': {
                    'info': ['GoodData'],
                    'warn': [],
                    'error': []
                }
            }
        }
        expected = 'Component Unit tests doesn\'t have status'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['componentResults'] = component_results
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_action_result_should_be_dict(self):
        expected = 'Action result must be dictionary'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['action'] = str()
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_action_result_should_have_message(self):
        action_result = {
            'status': 'OK',
        }
        expected = 'Action doesn\'t have message'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['action'] = action_result
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_validate_action_result_should_have_status(self):
        action_result = {
            'messages': {
                'info': [],
                'warn': [],
                'error': []
            }
        }
        expected = 'Action doesn\'t have status'
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        result.result['action'] = action_result
        with pytest.raises(smoker_exceptions.ValidationError) as exc_info:
            result.validate()
        assert expected in exc_info.value

    def test_set_result(self):
        result_to_validate = copy.deepcopy(self.result_to_validate)
        result = server_plugins.Result()
        result.set_result(result_to_validate, validate=True)
        assert result.validated

    def test_get_result(self):
        result = server_plugins.Result()
        result.result = copy.deepcopy(self.result_to_validate)
        assert not result.validated
        result.get_result()
        assert result.validated


def get_process_list():
    procs = dict()
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'cmdline'])
            procs[pinfo['pid']] = pinfo['cmdline'][0]
        except (psutil.NoSuchProcess, IndexError, TypeError):
            pass
    return procs


def random_string():
    return str(datetime.datetime.now().strftime("%y%m%d_%H%M%S%f"))
