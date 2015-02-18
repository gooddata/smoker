#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import logging
lg = logging.getLogger('smoker')

import threading
import urllib2
import simplejson
import time
import datetime

from smoker.util.progressbar import ProgressBar, NonInteractiveError

class Client(object):
    """
    Object providing access to the group of hosts
    """
    hosts = []

    def __init__(self, hosts):
        """
        Create Host objects
        """
        assert isinstance(hosts, list), "Parameter hosts should be list"

        pool = []
        lg.info("Loading info for %d hosts" % len(hosts))
        for host in hosts:
            host = Host(host)

            t = threading.Thread(target=host.load_about)
            t.daemon = True
            t.start()
            pool.append(t)
            self.hosts.append(host)
        self.wait(pool)

        # Check if hosts are OK and remove
        # broken ones
        i = len(self.hosts) - 1
        while i >= 0:
            host = self.hosts[i]
            if not host.links:
                del(self.hosts[i])
                lg.info("Removing %s from list of hosts" % host.name)
            i -= 1

    def get_plugins(self, filters=None, filters_negative=False, exclude_plugins=None):
        """
        Return dictionary of each host and plugin
        where plugin name is the key

        Accept filter argument to filter plugins
        by parameters

        filter = {
            'key'  : 'Category',
            'value': 'system'
        }

        result = {
            'Airy' : {
                'plugin1' : {...},
                'plugin2' : {...},
            },
            'Host2': {...}
        }
        """
        result = {}
        lg.info("Getting plugins for %d hosts" % len(self.hosts))
        plugins = self.open(resource='plugins')
        result = self._format_plugins(plugins, filters=filters, filters_negative=filters_negative, exclude_plugins=exclude_plugins)
        return PluginsResult(**result)

    def force_run(self, plugins, progress=True):
        """
        Force plugins run
        """
        # Map dictionary hostname -> Host object for easier access to it
        host_map = {}
        for host in self.hosts:
            host_map[host.name] = host

        pool = []
        # For each host in plugins result, force run of it's plugins
        for hostname, host in plugins.iteritems():
            t = threading.Thread(name=hostname, target=host_map[hostname].force_run, args=(host['plugins'],))
            t.daemon = True
            t.start()
            pool.append(t)

        if progress:
            self.wait_progress(pool)
        else:
            self.wait(pool)

        result = {}
        for hostname, host in plugins.iteritems():
            result[hostname] = host_map[hostname].get_result()

        result = self._format_plugins(result)
        return PluginsResult(**result)

    def _format_plugins(self, plugins, filters=[], filters_negative=False, exclude_plugins=None):
        """
        Format plugins result by host and it's status, apply filtering

        Example:
            result = {
                'host1': {
                    'status' : 'OK',
                    'plugins': {
                        'plugin_name' : ...
                    }
                }
            }

        :param plugins: PluginsResult object (expected dict behavior)
        :param filters: list of filters for plugin.match_filters() function
        :param negative: True if filters should be negative
        :param exclude_plugins: list of plugin names to exclude
        """
        result = {}
        for name, host in plugins.iteritems():
            # No plugins for host, skip it
            try:
                host['plugins']['items']
            except:
                continue

            for plugin in host['plugins']['items']:
                plugin = plugin['plugin']

                # Filter plugins
                match = self._match_filters(plugin, filters, negative=filters_negative, exclude_plugins=exclude_plugins)

                # Passed filter, update result
                if match:
                    # Create result structure if it doesn't exists
                    try:
                        result[name]
                    except:
                        result[name] = {
                            'status' : None,
                            'plugins': {},
                        }
                    result[name]['plugins'][plugin['name']] = plugin

                    # Update host status
                    if plugin['lastResult']:
                        if plugin['lastResult']['status'] == 'ERROR':
                            result[name]['status'] = 'ERROR'
                        elif plugin['lastResult']['status'] == 'WARN' and result[name]['status'] != 'ERROR':
                            result[name]['status'] = 'WARN'
                        else:
                            if result[name]['status'] not in ['ERROR', 'WARN']:
                                result[name]['status'] = 'OK'
        return result

    def _match_filters(self, plugin, filters, negative=False, exclude_plugins=None):
        """
        Check if plugin passes supplied filters

        :param plugin: plugin object
        :param filters: list of filters, filters can be special (key,value tuple), by parameters (dict) or list of plugin names (list)
        :param negative: True if filters should be negative
        :param exclude_plugins: list of plugin names to exclude
        :rvalue: bool
        """
        # Check if plugin is excluded
        if exclude_plugins:
            if plugin['name'] in exclude_plugins:
                return False

        # return True or False depending on negative variable
        match_result = lambda match: not match if negative else match

        match = True
        for filter in filters:
            # Special filters
            if isinstance(filter, tuple):
                key, value = filter
                # Filter by plugin status
                if key == 'status' and isinstance(value, list):
                    try:
                        if plugin['lastResult']['status'] in value:
                            match = True
                            if not negative: continue
                            else: break
                        else:
                            match = False
                            break
                    except (KeyError, TypeError):
                        # Unknown state - no plugin['lastResult']['status'] or it's NoneType
                        if 'UNKNOWN' in value:
                            match = True
                            if not negative: continue
                            else: break
                        else:
                            match = False
                            break
            # Filter by parameters
            elif isinstance(filter, dict):
                try:
                    if plugin['parameters'][filter['key']] == filter['value']:
                        lg.debug("Plugin %s matched filter %s = %s" % (plugin['name'], filter['key'], filter['value']))
                        match = True
                        if not negative: continue
                        else: break
                    else:
                        lg.debug("Plugin %s doesn't match filter %s = %s" % (plugin['name'], filter['key'], filter['value']))
                        match = False
                        break
                except KeyError:
                    lg.debug("Plugin %s doesn't have filter parameter %s" % (plugin['name'], filter['key']))
                    match = False
                    break
            # Filter by list of plugins
            elif isinstance(filter, list):
                if plugin['name'] in filter:
                    lg.debug("Plugin %s matched requested plugins list" % plugin['name'])
                    match = True
                    continue
                else:
                    match = False
                    lg.debug("Plugin %s doesn't match requested plugins list" % plugin['name'])
                    break

        match = match_result(match)
        return match

    def open(self, uri=None, resource=None, data=None):
        """
        Open given uri in parallel and
        get JSON-parsed result
        """
        if not uri and not resource:
            raise Exception("Argument uri or resource have to be submitted")

        pool = []
        for host in self.hosts:
            t = threading.Thread(name=host.name, target=host.open, args=(uri, resource, data,))
            t.daemon = True
            t.start()
            pool.append(t)

        self.wait(pool)

        result = {}
        for host in self.hosts:
            result[host.name] = host.get_result()

        return result

    def wait(self, pool):
        """
        Wait until all threads in pool are done
        """
        done = False
        while not done:
            done = True
            for t in pool:
                if t.isAlive():
                    done = False
            time.sleep(0.5)

    def wait_progress(self, pool):
        """
        Wait until all threads in pool are done
        and show nice progress bar
        """
        try:
            with ProgressBar(len(pool)) as progress:
                progress.wait_pool(pool)
        except NonInteractiveError as e:
            # Fallback to non-progress wait
            lg.warn(e)
            self.wait(pool)

class Host(object):
    """
    Object representing single smokerd server
    """
    name = None
    url = None
    address = None
    links = {}

    _result  = None

    def __init__(self, address):
        """
        Initialize object
        """
        host = address.split(':')
        try:
            port = host[1]
        except IndexError:
            port = 8086

        self.name = address
        self.url = "http://%s:%s" % (host[0], port)
        self.address = address
        self.links = {}
        self._result = None

    def load_about(self):
        """
        Load informations from about page
        """
        about = self.open('/', timeout=5)
        if about:
            self.name = about['about']['host']

            for link in about['about']['links']:
                self.links[link['rel']] = link
        else:
            return False

        return about

    def open(self, uri=None, resource=None, data=None, timeout=20):
        """
        Open given uri and get JSON-parsed result
        """
        if not uri and not resource:
            raise Exception("Argument uri or resource have to be submitted")

        if resource:
            try:
                uri = self.links[resource]['href']
            except KeyError:
                lg.error("Can't find resource %s" % resource)
                return False

        url = '%s%s' % (self.url, uri)
        lg.info("Host %s: requesting url %s" % (self.name, url))
        try:
            fh = urllib2.urlopen(url, timeout=timeout, data=data)
        except Exception as e:
            lg.error("Host %s: can't open resource %s: %s" % (self.name, url, e))
            return False

        try:
            json = simplejson.load(fh)
        except Exception as e:
            lg.error("Host %s: can't load response as JSON: %s" % (self.name, e))
            return False

        self._result = json
        return json

    def force_run(self, plugins):
        """
        Force plugin run
        Poll process until result

        plugins = {
            'pluginName' : {...},
            'pluginName2': {...},
        }
        """
        plugins_list = plugins.keys()
        data = simplejson.dumps({
            'process' : {
                'plugins' : plugins_list,
            }
        })

        lg.info("Forcing run of %d plugins on host %s" % (len(plugins_list), self.name))
        process = self.open(resource='processes', data=data)

        if process:
            poll = process['asyncTask']['link']['poll']
            return self.poll(uri=poll)
        else:
            return False

    def poll(self, uri, sleep=1):
        result = None
        retries = 3

        # Poll process for result
        while not result:
            res = self.open(uri=uri)

            if not res:
                if retries == 0:
                    lg.error(
                        "Polling on %s failed after 3 retries. This may "
                        "happen when a plugin died while waiting for the "
                        "result. Please retry and check log on the hosts if "
                        "it happens again." % uri)
                    return False
                else:
                    retries -= 1
                    continue

            if res.has_key('asyncTask'):
                uri = res['asyncTask']['link']['poll']
                time.sleep(1)
            else:
                result = res
        return result


    def get_result(self):
        """
        Return result and clear it
        """
        result = self._result
        self._result = None
        return result

class PluginsResult(dict):
    """
    Object for Client results
    """

    def __init__(self, *args, **kwargs):
        super(PluginsResult, self).__init__(*args, **kwargs)

        # Convert self structure to use PluginResult and HostResult instead of simple dict
        for name in self:
            self[name] = HostResult(self[name])
            for key in self[name]['plugins']:
                self[name]['plugins'][key] = PluginResult(self[name]['plugins'][key])

    def count_hosts(self):
        """
        Print number of hosts in result
        """
        return len(self)

    def get_host_plugins(self, host=None):
        """
        Return list of tuples with objects like:
        [(HostResult, PluginResult)]
        """
        result = []

        if not host:
            # Return all hosts
            for name in sorted(self):
                host = self[name]
                host['name'] = name
                for key in sorted(host['plugins']):
                    plugin = host['plugins'][key]
                    result.append((host, plugin))
        else:
            # Return only one host
            host = self[host]
            for key in sorted(host['plugins']):
                plugin = host['plugins'][key]
                result.append((host, plugin))
        return result

class PluginResult(dict):
    """
    Object for plugin result
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize dict and fix plugin structure
        """
        super(PluginResult, self).__init__(*args, **kwargs)
        self._fix_plugin()

    def _fix_plugin(self):
        """
        Fix plugin structure
        """
        # If plugin doesn't have lastResult, set it as unknown
        if not self['lastResult']:
            self['lastResult'] = {
                'status'   : 'UNKNOWN',
                'messages' : None,
                'componentResults' : None,
                'lastRun'  : None,
                }
        else:
            # convert lastRun to datetime object
            self['lastResult']['lastRun'] = datetime.datetime.strptime(self['lastResult']['lastRun'].partition('.')[0], "%Y-%m-%dT%H:%M:%S")

        if self['nextRun']:
            self['nextRun'] = datetime.datetime.strptime(self['nextRun'].partition('.')[0], "%Y-%m-%dT%H:%M:%S")

        return self

class HostResult(dict):
    """
    Object for Host result
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize dict and fix host structure
        """
        super(HostResult, self).__init__(*args, **kwargs)
        self._fix_host()

    def _fix_host(self):
        """
        Fix host structure
        """
        if not self['status']:
            self['status'] = 'UNKNOWN'

        return self
