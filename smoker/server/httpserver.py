#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Module providing base http server for smokerd REST API

Resource: about
    About page with links
    header: /

    GET
    - (200 OK) <About>  % self.print_about()

    (start example)
    {
       "about" : {
          "title" : "Smoker daemon API",
          "links" : [
             {
                "rel" : "plugins",
                "href" : "/plugins",
                "title" : "Show details about all plugins"
             },
             {
                "rel" : "plugin",
                "href" : "/plugins/<plugin>",
                "title" : "Show details about <plugin>"
             },
             {
                "rel" : "processes",
                "href" : "/plugins/processes",
                "title" : "Force plugin run"
             },
             {
                "rel" : "process",
                "href" : "/plugins/processes/<id>",
                "title" : "Poll process for result"
             }
          ]
       }
    }
    (end)

Resource: plugins
    Show active plugins details and result
    header: /plugins

    GET
    - (200 OK) <Plugins>    % self.print_plugins()

    (start example)
    {
       "plugins" : {
          "items" : [
             {
                "plugin" : {
                   "parameters" : {
                      "History" : 10,
                      "Interval" : 30,
                      "JMXBean" : "com.gooddata:name=SelfTest-connector",
                      "uid" : "default",
                      "JMXPort" : 5015,
                      "Module" : null,
                      "Parser" : "gdc.smoker.plugins.jmxparser",
                      "Enabled" : true,
                      "Template" : "JMXTest",
                      "Command" : "/Users/filip/gooddata/src/gdc-python/gdc-smokerd/bin/jmxcheck.py --port %(JMXPort)s --bean %(JMXBean)s --run %(JMXRun)s",
                      "Action" : null,
                      "Category" : "connectors",
                      "Timeout" : 10,
                      "gid" : "default",
                      "JMXRun" : "executeTestsJSON"
                   },
                   "nextRun" : "2012-10-26T13:31:56.814448",
                   "name" : "ConnectorZendesk3",
                   "lastResult" : {
                      "messages" : null,
                      "lastRun" : "2012-10-26T13:31:26.813870",
                      "status" : "ERROR",
                      "action" : null,
                      "componentResults" : [
                         {
                            "componentResult" : {
                               "messages" : {
                                  "info" : [],
                                  "warn" : [],
                                  "error" : [
                                     "SelfTest: Rabbit MQ service is NOT listening (host='localhost', port='5672')."
                                  ]
                               },
                               "status" : "ERROR",
                               "name" : "RabbitSelfTest"
                            }
                         },
                         {
                            "componentResult" : {
                               "messages" : {
                                  "info" : [
                                     "SelfTest: DB service is listening (host='localhost', port='3306')."
                                  ],
                                  "warn" : [],
                                  "error" : []
                               },
                               "status" : "OK",
                               "name" : "DBSelfTest"
                            }
                         },
                      ]
                   }
                }
             },
             {
                "plugin" : {
                   "parameters" : {
                      "History" : 10,
                      "Interval" : 2,
                      "uid" : "default",
                      "Module" : "gdc.smoker.plugins.uname",
                      "Enabled" : true,
                      "Parser" : null,
                      "Template" : null,
                      "Command" : null,
                      "Action" : null,
                      "Timeout" : 30,
                      "Category" : "system",
                      "gid" : "default"
                   },
                   "nextRun" : "2012-10-26T13:31:53.881718",
                   "name" : "Uname",
                   "lastResult" : {
                      "messages" : {
                         "info" : [
                            "Darwin Airy.local 12.2.0 Darwin Kernel Version 12.2.0: Sat Aug 25 00:48:52 PDT 2012; root:xnu-2050.18.24~1/RELEASE_X86_64 x86_64"
                         ],
                         "warn" : [],
                         "error" : []
                      },
                      "lastRun" : "2012-10-26T13:31:51.881592",
                      "status" : "OK",
                      "action" : null,
                      "componentResults" : null
                   }
                }
             }
          ]
       }
    }
    (end)

Resource: plugin
    Show single plugin details and results (with history)
    header: /plugins/<name>

    GET
    - (200 OK) <Plugin>     % self.print_plugins(name=<name>)

Resource: processes
    Force plugins run

    header: /plugins/processes

    POST <ForceRun>     % self.add_process()
    - (201 Created) <AsyncTask>
    - (400 Bad Request) % misunderstood JSON request

Resource: process
    Get result of forced run
    These resources will always return last forced result of each plugin,
    so it doesn't keep history!
    If you realy need it, it can be implemented, but now we don't want to keep
    history of forced run results.

    header: /plugins/processes/<id>

    GET
    - (200 OK) <Plugins>
    - (202 Accepted) <AsyncTask>    % we don't have results yet
    - (404 Not Found)
"""

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import socket
import logging

from smoker.server.exceptions import *

lg = logging.getLogger('smokerd.httpserver')

import simplejson as json

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer, object):
    """
    Threaded HTTPServer object
    """
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, smokerd):
        """
        Overwrite constructor to pass Smokerd instance
        """
        self.smokerd = smokerd
        self.pluginmgr = smokerd.pluginmgr

        super(ThreadedHTTPServer, self).__init__(server_address, RequestHandlerClass)

class HTTPHandler(BaseHTTPRequestHandler, object):
    """
    HTPServer requests handler
    """
    def __init__(self, *args):
        """
        Overwrite constructor of BaseHTTPRequestHandler

        Error = <error: {
            "component" : STRING,
            "code" : INT,
            "message" : STRING
        }>
        """
        # We want custom JSON-format errors instead of HTML
        self.error_message_format = json.dumps({
            'error': {
                'component' : 'Smoker',
                'code' : '%(code)s',
                'message' : '%(message)s',
            }
        })

        super(HTTPHandler, self).__init__(*args)

    def do_POST(self):
        """
        Serve POST requests
        """
        path = self.path.split('/')
        # Remove empty part before first /
        path.pop(0)

        try:
            resource = path[0]
        except IndexError:
            resource = None
            pass

        try:
            argument = path[1]
        except IndexError:
            argument = None
            pass

        try:
            id = path[2]
        except IndexError:
            id = None
            pass

        if resource == 'plugins' and argument == 'processes':
            length = int(self.headers.getheader('content-length'))
            request = self.rfile.read(length)

            try:
                js = json.loads(request)
            except json.JSONDecodeError as e:
                # Bad request, don't log
                self.return_400("Can't load submitted JSON: %s" % e.message)
                return
            except Exception as e:
                # Internal server error, log exception
                lg.error("Can't load submitted JSON: %s" % e)
                lg.exception(e)
                self.return_500("Can't load submitted JSON: %s" % e.message)
                return

            try:
                result = self.add_process(js)
            except InvalidArgument as e:
                # Invalid arguments supplied, raise bad request, don't log
                self.return_400(e.message)
                return
            except NoSuchPlugin as e:
                # Invalid arguments supplied, raise bad request, don't log
                self.return_400(e.message)
                return
            except NoPluginsFound:
                # Invalid arguments supplied, raise bad request, don't log
                self.return_400("No plugins was found by given names and filter")
                return
            except Exception as e:
                # Internal server error, log exception
                lg.error("Can't add submitted process: %s" % e)
                lg.exception(e)
                self.return_500("Can't add submitted process: %s" % e.message)
                return

            # Return 201 and location header to poll
            self.send_response(201)
            self.send_header('Content-type', 'application/json')
            self.send_header('Location', result['asyncTask']['link']['poll'])
            self.end_headers()

            self.wfile.write(json.dumps(result))
            return
        else:
            # Method not allowed on other resources
            self.return_405()

    def do_GET(self):
        """
        Serve GET requests
        """
        result = None
        path = self.path.split('/')
        # Remove empty part before first /
        path.pop(0)

        try:
            resource = path[0]
        except IndexError:
            resource = None
            pass

        try:
            argument = path[1]
        except IndexError:
            argument = None
            pass

        try:
            id = path[2]
        except IndexError:
            id = None
            pass

        if not resource:
            # Print about on index
            result = self.print_about()
        elif resource == 'plugins':
            if not argument:
                # Print all plugins information
                try:
                    result = self.print_plugins()
                except Exception as e:
                    lg.exception(e)
                    self.return_500(e.message)
                    return
            elif argument == 'processes':
                if id:
                    # Print result of given process
                    try:
                        result = self.print_process(id)
                    except InProgress:
                        # Return 202 and asyncTask structure
                        self.send_response(202, 'Accepted')
                        self.send_header('Location', self.path)
                        self.end_headers()
                        result = {
                            "asyncTask": {
                                "link": {
                                    "poll": self.path
                                }
                            }
                        }
                        self.wfile.write(json.dumps(result))
                        return
                    except IndexError:
                        self.return_404('Process id %s not found' % id)
                        return
                    except Exception as e:
                        lg.exception(e)
                        self.return_500(e.message)
                        return
                else:
                    # GET method on processes is not allowed
                    self.return_405()
                    return
            else:
                # Print single plugin informations
                try:
                    result = self.print_plugins(argument)
                except NoSuchPlugin:
                    self.return_404('Plugin %s not found' % argument)
                    return
                except Exception as e:
                    lg.exception(e)
                    self.return_500(e.message)
                    return
        elif resource == 'favicon.ico':
            try:
                self.return_favicon()
            except Exception as e:
                lg.exception(e)
                self.return_500(e.message)
                return
            return
        else:
            # Resource not found
            self.return_404()
            return

        # Print result
        if result:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')

            try:
                response = json.dumps(result)
            except Exception:
                self.return_500("Malformed JSON result")
                raise

            self.end_headers()
            self.wfile.write(response)
        else:
            self.return_500()

        return

    def return_favicon(self):
        """
        Open and return favicon.ico
        """
        try:
            fh = open(self.server.smokerd.conf['favicon'], 'r')
            self.send_response(200)
            self.send_header('Content-type', 'image/x-icon')
            self.end_headers()
            self.wfile.write(fh.read())
            fh.close()
        except:
            self.return_404()

    def return_500(self, msg='Unknown server error'):
        """
        Return 500 and optional message
        """
        self.send_error(500, msg)
        return

    def return_400(self, msg='Bad request'):
        """
        Return 400 to client with reason
        """
        self.send_error(400, msg)
        return

    def return_404(self, msg='Resource not found'):
        """
        Return 404 to client with reason
        """
        self.send_error(404, msg)
        return

    def return_405(self, msg='Method not allowed'):
        """
        Return 405 to client with reason
        """
        self.send_error(405, msg)
        return

    def print_about(self):
        """
        Print about page with title and links
        to all supported resources

        About = <about: {
            host  : STRING,
            title : STRING,
            links : [{
                'rel'  : STRING,
                'href' : URISTRING,
                'title': STRING,
            }]
        }>
        """
        result = {
            'about': {
                'host' : socket.gethostname(),
                'title': 'Smoker daemon API',
                'links'  : [
                    {
                        'rel'  : 'plugins',
                        'href' : '/plugins',
                        'title': 'Show details about all plugins',
                    },
                    {
                        'rel'  : 'processes',
                        'href' : '/plugins/processes',
                        'title': 'Force plugin run',
                    },
                ],
            },
        }
        return result

    def print_plugins(self, name=None):
        """
        Print informations for all plugins
        or for single plugin

        Plugins = <plugins: {
            "items" : [Plugin]
        }>

        Plugin = <plugin: {
            name : STRING,
            nextRun : ISOTIME | NULL,
            links   : {
                "self" : URISTRING
            }
            % One of Command or Module parameters must be set,
            % otherwise plugin won't be loaded
            parameters : {
                "Command" : STRING | NULL,
                "Module"  : STRING | NULL,
                "Parser"  : STRING | NULL,
                "Interval": INT,
                "Timeout" : INT,
                "History" : INT,
                "uid"     : 'default' | INT,
                "gid"     : 'default' | INT,
                "Template": STRING | NULL,
                "Action"  : {
                    "Command" : STRING | NULL,
                    "Module"  : STRING | NULL,
                    "Timeout" : INT
                } | NULL,
                ((STRING: STRING)*)?        % custom parameters are allowed
            },
            lastResult : Result | NULL,
            (results : [result: Result])?     % results history only on /plugins/<name>
        }>

        Result = {
            "status" : 'OK' | 'ERROR' | 'WARN',
            "lastRun"   : ISOTIME,
            "action" : Result | NULL,
            "messages" : Messages | NULL,
            "componentResults" : [componentResult: {
                "name" : STRING,
                "status"  : 'OK' | 'ERROR' | 'WARN',
                "messages": Messages
            }] | NULL
        }

        Messages = {
            "info" : [STRING],
            "error": [STRING],
            "warn" : [STRING]
        }
        """
        plugins = {}
        plugins_result = []

        if not name:
            plugins = self.server.pluginmgr.get_plugins()
        else:
            plugins[name] = self.server.pluginmgr.get_plugin(name)

        for pname, plugin in plugins.iteritems():
            # Convert next run object to ISO format
            if not isinstance(plugin.next_run, bool):
                next_run = plugin.next_run.isoformat()
            else:
                next_run = None

            # Convert result componentResults to list
            # just to have standarized API
            last_result = plugin.get_last_result()
            if last_result and last_result['componentResults']:
                # Remove reference, because we don't want to modify
                # Plugin object's structures
                last_result = dict(last_result)
                last_result['componentResults'] = self.to_list('componentResult', last_result['componentResults'])

            # Format plugin result
            plugin_result = {
                'name' : pname,
                'links': {
                    'self' : '/plugins/%s' % pname,
                },
                'parameters' : plugin.params,
                'lastResult' : last_result,
                'nextRun'    : next_run,
            }

            # Add results history only if we are listing single plugin
            if name:
                results = []
                for res in plugin.result:
                    # Remove reference, we don't want to edit Plugin object structures
                    res = dict(res)

                    # Convert result componentResults to list
                    # just to have standarized API
                    if res['componentResults']:
                        res['componentResults'] = self.to_list('componentResult', res['componentResults'])
                    results.append({'result': res})

                plugin_result['results'] = results

            plugins_result.append({'plugin': plugin_result})

        if name:
            return plugins_result[0]
        else:
            return { 'plugins' : {'items' : plugins_result} }

    def to_list(self, keyword, dictionary):
        """
        Convert dictionary to list by given keyword
        """
        result = []
        for key, value in dictionary.iteritems():
            res = value
            res['name'] = key
            result.append({keyword : res})

        return result

    def print_process(self, id):
        """
        Print process result
        """
        try:
            process = self.server.pluginmgr.get_process(int(id))
        except IndexError:
            raise

        results = []
        for plugin in process['plugins']:
            if not plugin.forced_result:
                raise InProgress
            else:
                # Remove reference, because we don't want to modify
                # Plugin object's structures
                forced_result = dict(plugin.forced_result)
                if forced_result['componentResults']:
                    forced_result['componentResults'] = self.to_list('componentResult', forced_result['componentResults'])

                # Convert next run object to ISO format
                if not isinstance(plugin.next_run, bool):
                    next_run = plugin.next_run.isoformat()
                else:
                    next_run = None

                result = {
                    'plugin' : {
                        'name'  : plugin.name,
                        'links': {
                            'self' : '/plugins/%s' % plugin.name,
                        },
                        'parameters' : plugin.params,
                        'lastResult': forced_result,
                        'nextRun'    : next_run,
                    }
                }
                results.append(result)

        return { 'plugins' : {'items' : results} }

    def add_process(self, definition):
        """
        Add new process

        AsyncTask = <asyncTask : {
            "link" : {
                "poll" : URISTRING
            }
        }>

        PostProcess = <process : {
            "plugins" : [STRING] | NULL,
            % filter is optional key : value pair of
            % plugin parameters to filter
            ("filter"  : { STRING : STRING } | NULL)?
        }>
        """
        if definition['process'].has_key("plugins"):
            plugins = definition['process']['plugins']
        else:
            plugins = None

        if definition['process'].has_key("filter"):
            filter = definition['process']['filter']
        else:
            filter = None

        # If plugins and filter are empty, raise exception
        if not plugins and not filter:
            raise InvalidArgument("Plugin names or filter have to be set")

        # Validate input
        if plugins and not isinstance(plugins, list):
            raise InvalidArgument("Element plugins have to be list")

        if filter and not isinstance(filter, dict):
            raise InvalidArgument("Element filter have to be dictionary")

        id = self.server.pluginmgr.add_process(plugins, filter)

        result = {
            'asyncTask': {
                'link': {
                    'poll': '/plugins/processes/%d' % id
                }
            }
        }

        return result
