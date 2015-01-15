# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved
"""
Module providing base http server for smokerd REST API
"""

from flask import Flask, request, make_response
from flask.ext.restful import Api, Resource, abort
import json
import multiprocessing
import setproctitle
import socket

from smoker.server import exceptions

# need to keep the daemon instance and common functions at module level since
# there's no other way how to pass the to Flask_restful class methods
smokerd = None


def next_run_iso_format(next_run):
    """
    Convert next run timestamp object to the ISO format
    """
    if isinstance(next_run, bool):
        next_run = None
    else:
        next_run = next_run.isoformat()


def standardized_api_list(component):
    """
    Convert result dict to list just to have standardized API
    """
    keyword = 'componentResults'

    if not component:
        return component
    if not component[keyword]:
        return component

    # Remove reference, because we don't want to modify
    # Plugin object's structures
    results = dict(component)
    results[keyword] = []
    for key, value in component[keyword].iteritems():
        value['name'] = key
        results[keyword].append({'componentResult': value})

    return results


def print_plugin(name, forced=False):
    """
    Print information about a plugin

    :param name: name of the plugin
    :type name: string
    :param forced: use forced_results instead of last_results
    :type forced: bool
    """

    plugin = smokerd.pluginmgr.get_plugin(name)

    # Format plugin result
    plugin_result = {
        'lastResult': standardized_api_list(plugin.get_last_result()),
        'links': {
            'self': '/plugins/%s' % name,
        },
        'name': name,
        'nextRun': next_run_iso_format(plugin.next_run),
        'parameters': plugin.params
    }

    if forced:
        if not plugin.forced_result:
            raise exceptions.InProgress
        plugin_result['forcedResult'] = plugin.forced_result
    return {'plugin': plugin_result}


def print_plugins(plugins, forced=False):
    """
    Print information about set of plugins

    :param plugins: list of plugin names
    :type plugins: list of strings
    :param forced: use forced_results instead of last_results
    :type forced: bool
    """
    plugins_result = []

    for plugin in plugins:
        plugins_result.append(print_plugin(plugin, forced))

    return {'plugins': {'items': plugins_result}}


def get_plugin_history(name):
    """
    Get history of results for single plugin

    :param name: name of the plugin
    :type name: string
    """
    plugin = smokerd.pluginmgr.get_plugin(name)
    results = []

    for res in plugin.result:
        res = standardized_api_list(res)
        results.append({'result': res})

    return results


def print_in_progress(id):
    """
    Format json info about process in progress

    :param id: process identifier
    :type id: int
    """
    location = '/processes/%d' % id
    data = {
        'asyncTask': {
            'link': {
                'poll': location
            }
        }
    }

    # need to create response manually in orted to have custom status code
    response = make_response(json.dumps(data, indent=2))
    response.status = 'Accepted'
    response.status_code = 202
    response.headers['Location'] = location
    response.headers['content-type'] = 'application/json'
    return response


class About(Resource):
    """
    Print the basic usage
    """
    def get(self):
        return {
            'about': {
                'host': socket.gethostname(),
                'title': 'Smoker daemon API',
                'links': [
                    {
                        'rel': 'plugins',
                        'href': '/plugins',
                        'methods': 'GET',
                        'title': 'Show details about all plugins'
                    },
                    {
                        'rel': 'processes',
                        'href': '/processes',
                        'methods': 'GET, POST',
                        'title': 'Force plugin run'
                    }
                ]
            }
        }


class Plugins(Resource):
    def get(self):
        """
        Print overview of all plugins
        """
        return print_plugins(smokerd.pluginmgr.get_plugins().keys())


class Plugin(Resource):
    def get(self, name):
        """
        Print a single plugin with history of results

        :param name: name of the plugin
        :type name: string
        """
        try:
            plugin = print_plugin(name)
        except exceptions.NoSuchPlugin as e:
            abort(404, message=e.message)
        history = get_plugin_history(name)
        plugin['results'] = history

        return plugin


class Processes(Resource):
    """
    Create or get process
    """
    def get(self):
        result = []
        processes = smokerd.pluginmgr.get_process_list()
        # we index processes from 1, having dummy on position 0
        for id in range(1, len(processes)):
            process = processes[id]
            plugins = []
            for plugin in process['plugins']:
                plugins.append(plugin.name)

            result.append(
                {
                    'href': 'processes/%d' % id,
                    'plugins': plugins
                }
            )
        return result

    def post(self):
        example = {}
        example['example_input'] = {
            'process': {
                'plugins': '[STRING] | NULL',
                'filter': '{STRING : STRING} | NULL'
            }
        }
        example['note'] = (
            'filter is optional key : value pair of plugin parameters '
            'to filter')

        definition = request.get_json(force=True)

        if (not definition or 'process' not in definition
                or not definition['process']):
            abort(400, **example)

        if 'plugins' in definition['process']:
            plugins = definition['process']['plugins']
        else:
            plugins = None

        if 'filter' in definition['process']:
            filter = definition['process']['filter']
        else:
            filter = None

        # If plugins and filter are empty, report bad request
        if not plugins and not filter:
            example['message'] = 'Plugin names or filter have to be set'
            abort(400, **example)

        # Validate input
        if plugins and not isinstance(plugins, list):
            example['message'] = 'Element plugins have to be list'
            abort(400, **example)

        if filter and not isinstance(filter, dict):
            example['message'] = 'Element filter have to be dictionary'
            abort(400, **example)

        try:
            id = smokerd.pluginmgr.add_process(plugins, filter)
        except Exception as e:
            abort(500, message=e.message)

        return print_in_progress(id)


class Process(Resource):
    def get(self, id):
        """
        Get single process result

        :param id: process identifier
        :type id: int
        """
        try:
            if id < 1:
                raise IndexError
            process = smokerd.pluginmgr.get_process(int(id))
        except IndexError:
            abort(404, message='Process id %s not found' % id)

        plugins = []
        for plugin in process['plugins']:
            plugins.append(plugin.name)

        try:
            return print_plugins(plugins, forced=True)
        except exceptions.InProgress:
            return print_in_progress(id)


class RestServer(multiprocessing.Process):
    def __init__(self, host, port, smoker_daemon):
        """
        :param host: host to bind the server to"
        :type host: string
        :param port: port to bind the server to"
        :type port: int
        :param smoker_daemon: instance of the smoker daemon
        :type smoker_daemon: smokerd.Smokerd
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)

        self.api = Api(self.app)
        self.api.add_resource(About, '/')
        self.api.add_resource(Plugins, '/plugins', '/plugins/')
        self.api.add_resource(Plugin, '/plugins/<string:name>',
                              '/plugins/<string:name>/')
        self.api.add_resource(Processes, '/processes', '/processes/')
        self.api.add_resource(Process, '/processes/<int:id>',
                              '/processes/<int:id>/')

        global smokerd
        smokerd = smoker_daemon

        super(RestServer, self).__init__()
        self.daemon = True

    def run(self):
        setproctitle.setproctitle('smokerd rest api server')
        self.app.run(self.host, self.port)
