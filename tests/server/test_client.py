#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved

import mock
import os
import pytest
import shutil
import smoker.client as smoker_client
from smoker.client import cli as smoker_cli
import socket
from tests.server.smoker_test_resources import client_mock_result
from tests.server.smoker_test_resources.client_mock_result\
    import rest_api_response
from tests.server.smoker_test_resources.client_mock_result import TMP_DIR


class TestHost(object):
    """Unit tests for the client.Host class"""

    hostname = socket.gethostname()

    def test_create_host_instance(self):

        host = smoker_client.Host('%s:8086' % self.hostname)
        assert host.url == 'http://%s:8086' % self.hostname
        assert not host.links

        host = smoker_client.Host('%s' % self.hostname)
        assert host.url == 'http://%s:8086' % self.hostname
        assert not host.links

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_load_about(self):
        # Mock: http://${hostname}:8089/  load_about
        host = smoker_client.Host('%s:8086' % self.hostname)
        assert not host.links
        assert host.load_about() == client_mock_result.about_response
        assert host.links == client_mock_result.links
        assert host.name == client_mock_result.about_response['about']['host']

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_result_will_be_cleared_after_getting(self):
        # Mock: http://${hostname}:8089/  load_about
        host = smoker_client.Host('%s:8086' % self.hostname)
        host.load_about()
        assert host.get_result() == client_mock_result.about_response
        assert not host.get_result()

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_force_run(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/processes  open(resource='processes')
        # Mock: http://${hostname}:8089/processes/#  open(uri='/processes/#')
        expected = client_mock_result.force_plugin_run_response['Uptime']
        host = smoker_client.Host('%s:8086' % self.hostname)
        host.load_about()
        plugins = {'Uptime': dict()}
        assert host.force_run(plugins)['plugins']['items'][0] == expected

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_force_run_with_invalid_plugin_name(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/processes  open(resource='processes')
        host = smoker_client.Host('%s:8086' % self.hostname)
        host.load_about()
        plugins = {'InvalidPlugin': dict()}
        assert host.force_run(plugins) is False
        assert host.get_result() == client_mock_result.about_response

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_load_about_before_open_resource(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/plugins  open(resource='plugins')
        host = smoker_client.Host('%s:8086' % self.hostname)
        assert not host.open(resource='plugins')
        host.load_about()
        assert host.open(resource='plugins')

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_open_with_invalid_uri_and_resource(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/InvalidUri  open(uri='/InvalidUri')
        # Mock: http://${hostname}:8089/InvalidResource
        #   open(resource='InvalidResource')
        expected_exc = 'Argument uri or resource have to be submitted'
        host = smoker_client.Host('%s:8086' % self.hostname)
        host.load_about()
        assert not host.open(uri='/InvalidUri')
        assert not host.open(resource='InvalidResource')
        with pytest.raises(Exception) as exc_info:
            host.open()
        assert expected_exc in exc_info.value


class TestClient(object):
    """Unit tests for the client.Client class"""

    hostname = socket.gethostname()

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_create_client_instance(self):
        # Mock: http://${hostname}:8089/  load_about
        cli = smoker_client.Client(['%s:8086' % self.hostname])
        assert cli.hosts[0].load_about() == client_mock_result.about_response

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_get_plugins_with_filter_is_none(self):
        cli = smoker_client.Client(['%s:8086' % self.hostname])
        with pytest.raises(TypeError) as exc_info:
            cli.get_plugins()
        assert "'NoneType' object is not iterable" in exc_info.value

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_get_plugins(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/plugins  open(resource='plugins')

        # Need confirm the format of filters. Look likes It doesn't work
        # filters = { 'Category': 'system'}
        # filters = ('Category', 'system')
        # filters = ['Uname', 'Uptime']
        cli = smoker_client.Client(['%s:8086' % self.hostname])
        result = cli.get_plugins(filters=list())
        assert self.hostname in result
        assert cli.hosts[0].load_about() == client_mock_result.about_response
        for x in ['Uname', 'Hostname', 'Uptime']:
            assert x in result[self.hostname]['plugins']

        result = cli.get_plugins(filters=list(), exclude_plugins=['Uname'])
        assert 'Hostname' and 'Uptime' in result[self.hostname]['plugins']
        assert 'Uname' not in result[self.hostname]['plugins']

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_open_with_invalid_uri_and_resource(self):
        # Mock: http://${hostname}:8089/  load_about
        cli = smoker_client.Client(['%s:8086' % self.hostname])
        expected_exc = 'Argument uri or resource have to be submitted'
        expected_response = client_mock_result.about_response
        assert cli.open(uri='/InvalidUri')[self.hostname] == expected_response
        cli.open(resource='InvalidResource') == expected_response
        with pytest.raises(Exception) as exc_info:
            cli.open()
        assert expected_exc in exc_info.value

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_force_run(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/processes  open(resource='processes')
        # Mock: http://${hostname}:8089/processes/#  open(uri='/processes/#')

        cli = smoker_client.Client(['%s:8086' % self.hostname])
        plugins = cli.get_plugins(filters=list(),
                                  exclude_plugins=['Hostname', 'Uname'])
        result = cli.force_run(plugins)[self.hostname]
        assert result['status'] == 'OK'
        result = result['plugins']
        assert 'Uptime' in result
        assert 'Uname' and 'Hostname' not in result
        assert 'forcedResult' in result['Uptime']
        assert result['Uptime']['forcedResult']['status'] == 'OK'
        assert result['Uptime']['links']['self'] == '/plugins/Uptime'

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_force_run_with_WARN_result(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/processes  open(resource='processes')
        # Mock: http://${hostname}:8089/processes/#  open(uri='/processes/#')

        cli = smoker_client.Client(['%s:8086' % self.hostname])
        plugins = cli.get_plugins(filters=list(),
                                  exclude_plugins=['Hostname'])
        result = cli.force_run(plugins)[self.hostname]

        assert result['status'] == 'WARN'
        result = result['plugins']
        assert 'Uptime' and 'Uname' in result
        assert 'Hostname' not in result
        assert 'forcedResult' in result['Uptime'] and result['Uname']
        assert result['Uptime']['forcedResult']['status'] == 'OK'
        assert result['Uname']['forcedResult']['status'] == 'WARN'
        assert result['Uptime']['links']['self'] == '/plugins/Uptime'
        assert result['Uname']['links']['self'] == '/plugins/Uname'

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_force_run_with_ERROR_result(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/processes  open(resource='processes')
        # Mock: http://${hostname}:8089/processes/#  open(uri='/processes/#')

        cli = smoker_client.Client(['%s:8086' % self.hostname])
        plugins = cli.get_plugins(filters=list())
        result = cli.force_run(plugins)[self.hostname]

        assert result['status'] == 'ERROR'
        result = result['plugins']
        assert 'Uptime' and 'Uname' and 'Hostname' in result
        assert 'forcedResult' in result['Uptime'] and result['Uname'] \
               and result['Hostname']
        assert result['Uptime']['forcedResult']['status'] == 'OK'
        assert result['Uname']['forcedResult']['status'] == 'WARN'
        assert result['Hostname']['forcedResult']['status'] == 'ERROR'
        assert result['Uptime']['links']['self'] == '/plugins/Uptime'
        assert result['Uname']['links']['self'] == '/plugins/Uname'
        assert result['Hostname']['links']['self'] == '/plugins/Hostname'

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_dump_tap_result(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/plugins  open(resource='plugins')

        cli = smoker_client.Client(['%s:8086' % self.hostname])

        plugins = cli.get_plugins(filters=list())
        expected = '\n'.join(client_mock_result.tap_result_all_plugins)
        assert smoker_cli.dump_tap(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Hostname'])
        expected = '\n'.join(client_mock_result.tap_result_uptime_uname)
        assert smoker_cli.dump_tap(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Uname'])
        expected = '\n'.join(client_mock_result.tap_result_uptime_hostname)
        assert smoker_cli.dump_tap(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Uptime'])
        expected = '\n'.join(client_mock_result.tap_result_hostname_uname)
        assert smoker_cli.dump_tap(plugins) == expected

    @mock.patch('urllib2.urlopen', rest_api_response)
    def test_plugins_to_xml_result(self):
        # Mock: http://${hostname}:8089/  load_about
        # Mock: http://${hostname}:8089/plugins  open(resource='plugins')

        cli = smoker_client.Client(['%s:8086' % self.hostname])

        plugins = cli.get_plugins(filters=list())
        expected = '\n'.join(client_mock_result.xml_result_all_plugins)
        assert smoker_cli.plugins_to_xml(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Hostname'])
        expected = '\n'.join(client_mock_result.xml_result_uptime_uname)
        assert smoker_cli.plugins_to_xml(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Uname'])
        expected = '\n'.join(client_mock_result.xml_result_uptime_hostname)
        assert smoker_cli.plugins_to_xml(plugins) == expected

        plugins = cli.get_plugins(filters=list(), exclude_plugins=['Uptime'])
        expected = '\n'.join(client_mock_result.xml_result_hostname_uname)
        assert smoker_cli.plugins_to_xml(plugins) == expected


class TestCleanUp(object):
    """Clean up all temporary files used by Mock"""
    def test_clean_up(self):
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
