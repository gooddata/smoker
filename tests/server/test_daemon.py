#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

from builtins import object
import copy
import datetime
import os
import pytest
from smoker.server.daemon import Smokerd


def generate_unique_file():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')


class TestDaemon(object):
    """Unit tests for the load_config functions"""
    conf_dir = (os.path.dirname(os.path.realpath(__file__)) +
                '/smoker_test_resources/smokerd')

    expected_basic = {
        'bind_host': '0.0.0.0',
        'bind_port': 8086,
        'pidfile': '/var/run/smokerd.pid',
        'stdin':  '/dev/null',
        'stdout': '/dev/null',
        'stderr': '/dev/null',
        'templates': {
            'BasePlugin': {
                'Timeout': 5,
                'History': 10
            }
        }
    }

    expected_plugins = {
        'plugins': {
            'uname': {
                'Category': 'system',
                'Interval': 1,
                'Module': 'smoker.server.plugins.uname'
            },
            'hostname': {
                'Category': 'system',
                'Interval': 1,
                'Command': 'hostname'
            },
            'uptime': {
                'Category': 'monitoring',
                'Interval': 1,
                'Command': 'uptime'
            }
        }
    }

    def test_load_config(self):
        yaml_file = self.conf_dir + '/smokerd.yaml'

        expected_plugins = copy.deepcopy(self.expected_plugins)
        expected = dict(expected_plugins, **copy.deepcopy(self.expected_basic))
        expected['config'] = yaml_file
        smokerd = Smokerd(config=yaml_file)
        assert smokerd.conf == expected

    def test_load_config_with_include(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())
        conf_smokerd = open(self.conf_dir + '/smokerd_basic.yaml', 'r').read()

        expected_plugins = copy.deepcopy(self.expected_plugins)
        expected = dict(expected_plugins, **copy.deepcopy(self.expected_basic))
        expected['config'] = yaml_file

        conf_plugins = [
            'plugins:',
            '    hostname: !include %s/plugins/hostname.yaml' % self.conf_dir,
            '    uptime: !include %s/plugins/uptime.yaml' % self.conf_dir,
            '    uname: !include %s/plugins/uname.yaml' % self.conf_dir
        ]
        conf_smokerd += '\n'.join(conf_plugins)

        with open(yaml_file, 'w') as fp:
            fp.write(conf_smokerd)

        smokerd = Smokerd(config=yaml_file)
        os.remove(yaml_file)
        assert smokerd.conf == expected

    def test_load_config_with_include_dir(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())
        expected = copy.deepcopy(self.expected_plugins)
        expected['config'] = yaml_file
        expected['bind_host'] = '0.0.0.0'
        expected['bind_port'] = 8086

        with open(yaml_file, 'w') as fp:
            fp.write('plugins: !include_dir %s/plugins\n' % self.conf_dir)
            fp.write('bind_host: 0.0.0.0\n')
            fp.write('bind_port: 8086\n')
        smokerd = Smokerd(config=yaml_file)
        os.remove(yaml_file)
        assert smokerd.conf == expected

    def test_load_config_with_include_files(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())

        expected = copy.deepcopy(self.expected_plugins)
        expected['config'] = yaml_file

        conf_plugins = [
            'plugins:',
            '    hostname: !include %s/plugins/hostname.yaml' % self.conf_dir,
            '    uptime: !include %s/plugins/uptime.yaml' % self.conf_dir,
            '    uname: !include %s/plugins/uname.yaml' % self.conf_dir
        ]

        with open(yaml_file, 'w') as fp:
            fp.write('\n'.join(conf_plugins))

        smokerd = Smokerd(config=yaml_file)
        os.remove(yaml_file)
        assert smokerd.conf == expected

    def test_load_config_with_include_dir_only(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())
        expected = copy.deepcopy(self.expected_plugins)
        expected['config'] = yaml_file

        with open(yaml_file, 'w') as fp:
            fp.write('plugins: !include_dir %s/plugins' % self.conf_dir)
        smokerd = Smokerd(config=yaml_file)
        os.remove(yaml_file)
        assert smokerd.conf == expected

    def test_load_config_with_invalid_file_path(self):
        expected = 'No such file or directory'
        with pytest.raises(IOError) as exc_info:
            Smokerd(config='InvalidFilePath')
        assert expected in repr(exc_info.value)

    def test_load_config_with_invalid_include_file_path(self):
        expected = 'No such file or directory'

        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())
        with open(yaml_file, 'w') as fp:
            fp.write('plugins: !include /InvalidFilePath')

        with pytest.raises(IOError) as exc_info:
            Smokerd(config=yaml_file)
        assert expected in repr(exc_info.value)
        os.remove(yaml_file)

    def test_load_config_with_invalid_include_dir_path(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())
        with open(yaml_file, 'w') as fp:
            fp.write('plugins: !include_dir /InvalidFilePath')

        smokerd = Smokerd(config=yaml_file)
        assert 'plugins' in smokerd.conf
        assert not smokerd.conf['plugins']
        os.remove(yaml_file)

    def test_load_config_with_invalid_yaml_format(self):
        yaml_file = '%s/%s.yaml' % (self.conf_dir, generate_unique_file())

        with open(yaml_file, 'w') as fp:
            fp.write('plugins InvalidFormat')
        with pytest.raises(AttributeError) as exc_info:
            Smokerd(config=yaml_file)
        assert "'str' object has no attribute 'items'" in repr(exc_info.value)
        os.remove(yaml_file)

        with open(yaml_file, 'w') as fp:
            fp.write('- plugins InvalidFormat')
        with pytest.raises(AttributeError) as exc_info:
            Smokerd(config=yaml_file)
        assert "'list' object has no attribute 'items'" in repr(exc_info.value)
        os.remove(yaml_file)

    def test_load_config_from_default_path(self):
        # Any solution to test this case
        # default smoker.yaml is different across nodes
        pass
