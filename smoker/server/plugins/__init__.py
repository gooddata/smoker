#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import datetime
import logging
import multiprocessing
import os
import re
import signal
import simplejson
import setproctitle
import time
import types

from smoker.server.exceptions import *
import smoker.util.command

lg = logging.getLogger('smokerd.pluginmanager')

# Initialize multiprocessing semamphore, by default limit by
# number of online CPUs + 2
semaphore_count = int(os.sysconf('SC_NPROCESSORS_ONLN')) + 2
lg.info("Plugins will run approximately at %s parallel processes" % semaphore_count)
semaphore = multiprocessing.Semaphore(semaphore_count)


def alarm_handler(signum, frame):
    raise PluginExecutionTimeout


class PluginManager(object):
    """
    PluginManager provides management and
    access to plugins
    """
    # Configured plugins/templates/actions
    conf_plugins   = None
    conf_actions   = None
    conf_templates = None

    # Plugin objects
    plugins = {}

    # Processes
    processes = []
    # We don't want to have process ID 0 (first index)
    # so fill it by None
    processes.append(None)

    def __init__(self, plugins=None, actions=None, templates=None):
        """
        PluginManager constructor
         * load plugins/templates/actions configuration
         * create plugins objects
        """
        self.conf_plugins   = plugins
        self.conf_actions   = actions
        self.conf_templates = templates

        self.stopping = False

        # Load Plugin objects
        self.load_plugins()

    def start(self):
        """
        Start all plugins
        """
        for name, plugin in self.plugins.iteritems():
            plugin.start()

    def stop(self, blocking=True):
        """
        Stop all plugins
        Wait until they are stopped if blocking=True
        """
        self.stopping = True

        # Trigger stop of all plugins
        for name, plugin in self.plugins.iteritems():
            plugin.stop()
            plugin.terminate()

        # Wait until all plugins are stopped
        if blocking:
            plugins_left = self.plugins.keys()
            plugins_left_cnt = len(plugins_left)
            while plugins_left:
                plugins_left = []
                for name, plugin in self.plugins.iteritems():
                    if plugin.is_alive():
                        plugins_left.append(name)
                    else:
                        plugin.join()
                if plugins_left:
                    # Print info only if number of left plugins changed
                    if len(plugins_left) != plugins_left_cnt:
                        lg.info("Waiting for %s plugins to shutdown: %s" % (len(plugins_left), ','.join(plugins_left)))
                    plugins_left_cnt = len(plugins_left)
                    time.sleep(0.5)

    def load_plugins(self):
        """
        Create Plugin objects
        """
        # Check if BasePlugin template is present
        # or raise exception
        try:
            self.get_template('BasePlugin')
        except (TemplateNotFound, NoTemplatesConfigured):
            lg.error("Required BasePlugin template is not configured!")
            raise BasePluginTemplateNotFound

        for plugin, options in self.conf_plugins.iteritems():
            if options.has_key('Enabled') and options['Enabled'] == False:
                lg.info("Plugin %s is disabled, skipping.." % plugin)
                continue

            try:
                self.plugins[plugin] = self.load_plugin(plugin, options)
            except TemplateNotFound:
                lg.error("Can't find configured template %s for plugin %s, plugin not loaded" % (options['Template'], plugin))
                continue
            except NoTemplatesConfigured:
                lg.error("There are no templates configured, template %s is required by plugin %s, plugin not loaded" % (options['Template'], plugin))
                continue
            except AssertionError as e:
                lg.error("Plugin %s not loaded: AssertionError, %s" % (plugin, e))
                continue
            except Exception as e:
                lg.error("Plugin %s not loaded: %s" % (plugin, e))
                lg.exception(e)
                continue
            lg.info("Loaded plugin %s" % plugin)

        if len(self.plugins) == 0:
            lg.error("No plugins loaded!")
            raise NoRunningPlugins("No plugins loaded!")

    def load_plugin(self, plugin, options):
        """
        Create and return Plugin object
        """
        # Load BasePlugin template first
        try:
            template = self.get_template('BasePlugin')
        except:
            template = {}

        # Plugin has template, load it's parent params
        if options.has_key('Template'):
            template_custom = self.get_template(options['Template'])
            template = dict(template, **template_custom)

        if options.has_key('Action'):
            options['Action'] = self.get_action(options['Action'])

        params = dict(template, **options)
        return Plugin(plugin, params)

    def restart_plugin(self, name):
        lg.info("Restarting plugin %s" % name)
        self.plugins[name].join()

        self.plugins[name] = self.load_plugin(name, self.conf_plugins[name])
        self.plugins[name].start()


    def get_template(self, name):
        """
        Return template parameters
        """
        if not isinstance(self.conf_templates, dict):
            raise NoTemplatesConfigured

        try:
            params = self.conf_templates[name]
        except KeyError:
            raise TemplateNotFound("Can't find configured template %s" % name)

        return params

    def get_action(self, name):
        """
        Return template parameters
        """
        if not isinstance(self.conf_actions, dict):
            raise NoActionsConfigured

        try:
            params = self.conf_actions[name]
        except KeyError:
            raise ActionNotFound("Can't find configured action %s" % name)

        return params

    def get_plugins(self, filter=None):
        """
        Return all plugins or filter them by parameter
        """

        if filter:
            plugins = []
            key = filter.keys()[0]
            value = filter[key]

            for plugin in self.plugins.itervalues():
                if plugin.params.has_key(key):
                    if plugin.params[key] == value:
                        plugins.append(plugin)
            return plugins
        else:
            return self.plugins

    def get_plugin(self, name):
        """
        Return single plugin
        """
        try:
            return self.plugins[name]
        except KeyError:
            raise NoSuchPlugin("Plugin %s not found" % name)

    def add_process(self, plugins=None, filter=None):
        """
        Add process and force plugin run
        """
        plugins_list = []

        # Add plugins by name
        if plugins:
            for plugin in plugins:
                plugins_list.append(self.get_plugin(plugin))

        # Add plugins by filter
        if filter:
            plugins_list.extend(self.get_plugins(filter))

        # Raise exception if no plugins was found
        if len(plugins_list) == 0:
            raise NoPluginsFound

        process = {
            'plugins' : plugins_list,
        }

        plugins_name = []
        for p in plugins_list:
            plugins_name.append(p.name)

        lg.info("Forcing run of %d plugins: %s" % (len(plugins_list), ', '.join(plugins_name)))

        # Add process into the list
        self.processes.append(process)
        id = len(self.processes)-1

        # Force run for each plugin and clear forced_result
        for plugin in plugins_list:
            plugin.forceFlag.set()
            plugin.forced_result = None

        return id

    def get_process(self, id):
        """
        Return process
        """
        return self.processes[id]

    def get_process_list(self):
        """
        Return all processes
        """
        return self.processes


class Plugin(multiprocessing.Process):
    """
    Object that represents single plugin
    """
    name = None
    params = {}

    params_default = {
        'Command' : None,
        'Module'  : None,
        'Parser'  : None,
        'Interval': 0,
        'Timeout' : 1800,
        'History' : 10,
        'uid'     : 'default',
        'gid'     : 'default',
        'Template': None,
        'Action'  : None,
    }

    def __init__(self, name, params):
        """
        Plugin constructor
         * prepare the process

        :param name: name of the plugin
        :type name: string

        :param params: keyword arguments
        :type params: dict
        """
        assert isinstance(name, basestring)
        assert isinstance(params, dict)
        self.name = name
        self.params = dict(self.params_default, **params)
        self.stopping = False

        # Set Action properly to have all
        # required default parameters
        if self.params['Action']:
            action_default = {
                'Command' : None,
                'Module'  : None,
                'Timeout' : 60,
            }
            self.params['Action'] = dict(action_default, **params['Action'])

        # create the instances of the Queue and force flag
        self.queue = multiprocessing.Queue()
        self.forceFlag = multiprocessing.Event()

        # Set those variables or they will be
        # references, shared between plugins
        self.result = []
        self.forced_result = None
        self.next_run = False

        # Validate configuration
        self.validate()

        # Drop privileges
        if self.params['uid'] != 'default' or self.params['gid'] != 'default':
            lg.debug("Plugin %s: dropping privileges to %s/%s" % (self.name, self.params['uid'], self.params['gid']))
            try:
                os.setegid(self.params['gid'])
                os.seteuid(self.params['uid'])
            except TypeError as e:
                lg.error("Plugin %s: config parameters uid/gid have to be integers: %s" % (self.name, e))
                raise
            except OSError as e:
                lg.error("Plugin %s: can't switch effective UID/GID to %s/%s: %s" % (self.name, self.params['uid'], self.params['gid'], e))
                raise

        # Schedule first plugin run
        if self.params['Interval']:
            self.schedule_run()

        # Run Process constructor, we want to be daemonic process
        super(Plugin, self).__init__()
        self.daemon = True

    def stop(self):
        """
        Set stopping variable
        """
        self.stopping = True
        return self.stopping

    def validate(self):
        """
        Validate configuration
        Raise InvalidConfiguration exception if invalid
        """
        # Timeout can't be 0 or less
        if self.params['Timeout'] <= 0:
            raise InvalidConfiguration("Timeout parameter can't be 0")

        # Command or Module have to be set
        if not self.params['Command'] and not self.params['Module']:
            raise InvalidConfiguration("Command or Module parameter has to be set")

        # Command and Module params can't be together
        if self.params['Command'] and self.params['Module']:
            raise InvalidConfiguration("Command and Module parameters cannot be set together")

        # Parser can't be set without command
        if not self.params['Command'] and self.params['Parser']:
            raise InvalidConfiguration("Parser can be used only with Command parameter")

    def run(self):
        """
        Run process
        Check if plugin should be run and execute it
        """
        setproctitle.setproctitle('smokerd plugin %s' % self.name)
        try:
            while self.stopping is not True:
                # Plugin run when forced
                if self.forceFlag.is_set():
                    with semaphore:
                        self.run_plugin(force=True)
                    self.forceFlag.clear()
                else:
                    # Plugin run in interval
                    if self.params['Interval']:
                        if datetime.datetime.now() >= self.next_run:
                            with semaphore:
                                self.run_plugin()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        # Stop the process
        lg.info("Shutting down plugin %s" % self.name)

    def schedule_run(self, time=None, now=False):
        """
        Schedule next plugin run
        Accept datetime object as time parameter or set
        current time if now parameter is True
        """
        if time:
            if isinstance(time, object) and type(time).__name__ == 'datetime':
                self.next_run = time
            else:
                raise InvalidArgument('Parameter time has to be an instance of datetime object')
        elif now == True:
            self.next_run = datetime.datetime.now()
        else:
            if self.params['Interval']:
                self.next_run = datetime.datetime.now() + datetime.timedelta(seconds=self.params['Interval'])

    def run_command(self, command, timeout=0):
        """
        Run system command and parse output
        """
        result = Result()
        lg.debug("Plugin %s: executing command %s" % (self.name, command))

        # Prepare params for stdin
        tmp = os.tmpfile()
        tmp.write(simplejson.dumps(dict(self.params, **self.get_last_result(True))))

        try:
            stdout, stderr, returncode = smoker.util.command.execute(command, timeout=timeout, stdin=tmp)
        except smoker.util.command.ExecutionTimeout as e:
            raise PluginExecutionTimeout(e)
        except Exception as e:
            lg.exception(e)
            raise PluginExecutionError("Can't execute command %s: %s" % (command, e))

        if returncode:
            status = 'ERROR'
        else:
            status = 'OK'

        # Run parser or parse output from stdin
        if self.params['Parser']:
            try:
                result = self.run_parser(stdout, stderr)
            except Exception as e:
                # Error result
                result.set_status('ERROR')
                result.add_error(re.sub('^\n', '', stderr.strip()))
                result.add_error('Parser run failed: %s' % e)
                result.add_info(re.sub('^\n', '', stdout.strip()))
        else:
            # Try to parse JSON output
            json = None
            try:
                json = simplejson.loads(stdout)
            except:
                pass

            if json:
                # Output is JSON, check it has valid status or raise exception
                if json.has_key('status') and json['status'] in [ 'OK', 'ERROR', 'WARN' ]:
                    try:
                        result.set_result(json, validate=True)
                    except ValidationError as e:
                        raise PluginMalformedOutput("Invalid JSON structure: %s" % e)
                else:
                    raise PluginMalformedOutput("Missing status in JSON output: %s" % json)
            else:
                # Output is not JSON, use stdout/stderr and return value
                lg.debug("Plugin %s: using non-JSON output" % self.name)
                result.set_status(status)
                if stderr:
                    result.add_error(re.sub('^\n', '', stderr.strip()))
                if stdout:
                    result.add_info(re.sub('^\n', '', stdout.strip()))

        return result

    def run_parser(self, stdout, stderr):
        """
        Run parser on given stdout/stderr
        Raise exceptions if anything happen
        """
        lg.debug("Plugin %s: running parser %s" % (self.name, self.params['Parser']))

        if stdout:
            lg.debug("Plugin %s: stdout: %s" % (self.name, stdout.strip()))
        if stderr:
            lg.debug("Plugin %s: stderr: %s" % (self.name, stderr.strip()))

        try:
            parser = __import__(self.params['Parser'], globals(), locals(), ['Parser'], -1)
        except ImportError as e:
            lg.error("Plugin %s: can't load parser %s: %s" % (self.name, self.params['Parser'], e))
            raise

        try:
            parser = parser.Parser(stdout, stderr)
        except Exception as e:
            lg.error("Plugin %s: can't initialize parser: %s" % (self.name, e))
            lg.exception(e)
            raise

        try:
            result = parser.parse()
        except Exception as e:
            lg.error("Plugin %s: parser execution failed: %s" % (self.name, e))
            lg.exception(e)
            raise

        return result

    def run_module(self, module, **kwargs):
        """
        Run Python module
        Raise exceptions if anything happen
        """
        lg.debug("Plugin %s: running module %s" % (self.name, module))
        try:
            plugin = __import__(module, globals(), locals(), ['Plugin'], -1)
        except ImportError as e:
            lg.error("Plugin %s: can't load module %s: %s" % (self.name, module, e))
            raise

        try:
            plugin = plugin.Plugin(self, **kwargs)
        except Exception as e:
            lg.error("Plugin %s: can't initialize plugin module: %s" % (self.name, e))
            lg.exception(e)
            raise

        signal.signal(signal.SIGALRM, alarm_handler)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.get_param('Timeout', default=120)

        try:
            signal.alarm(kwargs['timeout'])
            result = plugin.run()
        except PluginExecutionTimeout:
            result = Result()
            result.set_status('ERROR')
            result.add_error('Plugin execution exceeded timeout %d seconds' %
                             kwargs['timeout'])
        except Exception as e:
            lg.error("Plugin %s: module execution failed: %s" % (self.name, e))
            lg.exception(e)
            signal.alarm(0)
            raise

        signal.alarm(0)
        return result

    def run_plugin(self, force=False):
        """
        Run plugin, save result and schedule next run

        :param force: forced run
        :type force: bool
        """
        # External command will be executed
        if self.params['Command']:
            # Add parameters to command with format
            params = dict(self.params, **self.get_last_result(True))
            params = self.escape(params)
            command = self.params['Command'] % params
            # Execute external command to get result
            try:
                result = self.run_command(command, self.params['Timeout'])
            except Exception as e:
                lg.error("Plugin %s: %s" % (self.name, e))
                result = Result()
                result.set_status('ERROR')
                result.add_error(e)
        # Python module will be executed
        elif self.params['Module']:
            try:
                result = self.run_module(self.params['Module'])
            except Exception as e:
                lg.error("Plugin %s: %s" % (self.name, e))
                result = Result()
                result.set_status('ERROR')
                result.add_error(re.sub('^\n', '', ('%s' % e).strip()))
        # No module or command to run
        else:
            lg.error("Plugin %s: no Command or Module to execute!" % self.name)
            result = Result()
            result.set_status('ERROR')
            result.add_error('No Command or Module to execute!')

        # Run action on result
        if self.params['Action']:
            lg.debug("Plugin %s: executing action" % self.name)
            # Execute external command
            if self.params['Action']['Command']:
                # Add parameters to command with format
                params = dict(self.params, **result)
                params = self.escape(params)

                try:
                    action = self.run_command(self.params['Action']['Command'] % params, timeout=self.params['Action']['Timeout'])
                except Exception as e:
                    lg.error("Plugin %s: %s" % (self.name, e))
                    action = Result()
                    action.set_status('ERROR')
                    action.add_error(e)
            # Execute Python module
            elif self.params['Action']['Module']:
                try:
                    action = self.run_module(self.params['Action']['Module'], result=result)
                except Exception as e:
                    lg.error("Plugin %s: %s" % (self.name, e))
                    action = Result()
                    action.set_status('ERROR')
                    action.add_error(e)
            # No command or module to execute
            else:
                lg.error("Plugin %s: no Action Command or Module to execute!" % self.name)
                action = Result()
                action.set_status('ERROR')
                action.add_error('No Command or Module to execute!')
            # Add action result to plugin result
            result.set_action(action)

        result.set_forced(force)
        # send to the daemon
        try:
            self.queue.put(result.get_result())
        except ValidationError as e:
            lg.error("Plugin %s: ValidationError: %s" % (self.name, e))
            result = Result()
            result.set_status('ERROR')
            result.add_error('ValidationError: %s' % e)
            result.set_forced(force)
            self.queue.put(result.get_result())

        # Log result
        lg.info("Plugin %s result: %s" % (self.name, result.get_result()))

        # Finally schedule next run
        self.schedule_run()

    def get_last_result(self, dictionary=False):
        """
        Get last run result or False
        If dictionary=True, then return value will be always dict
        eg. for use like dict(self.params, **self.get_last_result(True))
        """
        while not self.queue.empty():
            self.result.append(self.queue.get())
            # Remove earliest result to keep only number
            # of results by parameter
            if len(self.result) > self.params['History']:
                self.result.pop(0)

        try:
            res = self.result[-1]
        except IndexError:
            if dictionary:
                return {}
            else:
                return None

        if res and res['forced'] and not self.forceFlag.is_set():
           self.forced_result = res

        return res

    def escape(self, tbe):
        """
        Escape given string, dictionary or list
        If int, None or bool item is found, just pass
        Also pass if item can't be escaped by some other reason
        Raise exception if unknown data type
        """
        if isinstance(tbe, dict):
            escaped = {}
            for key, value in tbe.iteritems():
                if type(value) in [int, types.NoneType, bool]:
                    escaped[key] = value
                else:
                    try:
                        escaped[key] = re.escape(value)
                    except:
                        escaped[key] = value
        elif isinstance(tbe, basestring):
            try:
                escaped = re.escape(tbe)
            except:
                escaped = tbe
        elif isinstance(tbe, int) or isinstance(tbe, bool):
            escaped = tbe
        elif isinstance(tbe, list):
            escaped = []
            for value in tbe:
                if type(value) in [int, types.NoneType, bool]:
                    escaped.append(value)
                else:
                    try:
                        escaped.append(re.escape(value))
                    except:
                        escaped.append(value)
        else:
            raise Exception("Unknown data type")

        return escaped

    def get_param(self, name, default=None):
        """
        Get plugin parameter
        Return default if parameter doesn't exist
        """
        try:
            return self.params[name]
        except KeyError:
            return default

class Result(object):
    """
    Object that represents plugin result
    """
    validated = False

    def __init__(self):
        """
        Default result values
        """
        self.result = {
            'status': None,
            'messages': None,
            'lastRun': datetime.datetime.now().isoformat(),
            'componentResults': None,
            'action': None,
            'forced': False
        }

    def set_status(self, status=None):
        """
        Set result status
        If status is empty, generate it from componentResults
        """
        if status is None:
            if not self.result['componentResults']:
                raise Exception("Can't generate overall status without component results")
            status = self._gen_component_status()

        if status not in ['OK', 'ERROR', 'WARN']:
            raise InvalidArgument("Status has to be OK, ERROR or WARN")

        self.result['status'] = status

    def _gen_component_status(self, default='OK'):
        """
        Generate status from component results
        """
        status = default
        for result in self.result['componentResults'].itervalues():
            if result['status'] == 'OK' and status not in ['WARN', 'ERROR']:
                status = 'OK'
            elif result['status'] == 'WARN' and status != 'ERROR':
                status = 'WARN'
            elif result['status'] == 'ERROR':
                status = 'ERROR'
        return status

    def set_forced(self, forced=True):
        self.result['forced'] = forced

    def add_info(self, msg):
        """
        Add info messge
        """
        self.add_msg('info', msg)

    def add_error(self, msg):
        """
        Add error messge
        """
        self.add_msg('error', msg)

    def add_warn(self, msg):
        """
        Add warn messge
        """
        self.add_msg('warn', msg)

    def add_msg(self, level, msg, multiline=False):
        """
        Add message into result
        Empty messages are skipped

        multiline - don't split message lines into
            multiple messages
        """
        # Create messages structure if it doesn't exists
        if not self.result['messages']:
            self.result['messages'] = {
                'info' : [],
                'error': [],
                'warn' : [],
            }

        if not multiline:
            messages = str(msg).split('\n')
        else:
            messages = [str(msg)]

        for message in messages:
            # Skip adding empty message
            if not str(msg).strip():
                continue

            try:
                self.result['messages'][level].append(str(message).strip())
            except KeyError:
                raise InvalidArgument("Level has to be info, error or warn")

    def validate(self, force=False):
        """
        Validate result
        Skip if it was already validated to avoid
        unwanted re-validation
        """
        if force != True and self.validated == True:
            return True
        else:
            try:
                self._validate_status(self.result['status'])
                self._validate_msg(self.result['messages'])
                self._validate_component_result(self.result['componentResults'])
                self._validate_action(self.result['action'])
            finally:
                self.validated = True

    def _validate_status(self, status):
        """
        Validate result status
        """
        if status not in ['OK', 'ERROR', 'WARN']:
            raise ValidationError("Result status has to be OK, ERROR or WARN, not %s" % status)

    def _validate_msg(self, msg):
        types = ['info', 'error', 'warn']
        if type(msg).__name__ not in ['NoneType', 'dict']:
            raise ValidationError("Result message has to be a dictionary or None, not %s" % type(msg).__name__)

        if msg:
            # Check every output type and validate it
            for t in types:
                try:
                    if not isinstance(msg[t], list):
                        raise ValidationError("Result message type %s has to be a list, not %s" % (t, type(msg[t]).__name__))
                    for out in msg[t]:
                        if not isinstance(out, basestring):
                            raise ValidationError("Result message type %s has to be a string, not %s" % (t, type(out).__name__))
                except Exception as e:
                    raise ValidationError("Can't validate message: %s" % e)

    def _validate_component_result(self, result):
        """
        Validate componentResults
        """
        # Component result can be empty
        if result == None:
            return True

        if not isinstance(result, dict):
            raise ValidationError("Component result must be dictionary")

        for name, component in result.iteritems():
            try:
                self._validate_msg(component['messages'])
            except KeyError:
                raise ValidationError("Component %s doesn't have message" % name)

            try:
                self._validate_status(component['status'])
            except KeyError:
                raise ValidationError("Component %s doesn't have status" % name)

    def _validate_action(self, result):
        """
        Validate action result
        """
        # Action can be empty
        if result == None:
            return True

        if not isinstance(result, dict):
            raise ValidationError("Action result must be dictionary")

        try:
            self._validate_msg(result['messages'])
        except KeyError:
            raise ValidationError("Action doesn't have message")

        try:
            self._validate_status(result['status'])
        except KeyError:
            raise ValidationError("Action doesn't have status")

    def set_result(self, result, validate=False):
        """
        Set result
        Not all fields have to be filled

        This method should be rarely used because it can
        cause invalid results

        Use validate=True and catch ValidationError to ensure
        given result is correct

        Result = <{
            'status'   : 'OK' | 'WARN' | 'ERROR',
            'messages' : Messages | NULL,
            'componentResults' : (STRING : {
                'status'  : 'OK' | 'WARN' | 'ERROR',
                'messages': Messages
            })* | NULL,
            'action'   : Result | NULL
        }>

        Messages = {
            'info' : [STRING],
            'error': [STRING],
            'warn' : [STRING]
        }
        """
        fields = [ 'status', 'messages', 'componentResults', 'action' ]

        for field in fields:
            try:
                self.result[field] = result[field]
            except KeyError:
                # just skip missing fields
                pass

        if validate == True:
            self.validate()

    def get_result(self, validate=True):
        """
        Validate by default and return result
        """
        if validate == True:
            self.validate()
        return self.result

    def set_action(self, action):
        """
        Set action result
        """
        if isinstance(action, object):
            self.result['action'] = action.get_result()
        elif isinstance(action, dict):
            self.result['action'] = action
        else:
            raise InvalidArgument("Action has to be a dict or a Result object")

    def add_component(self, name, status, info=[], error=[], warn=[]):
        """
        Add component result
        """
        if not self.result['componentResults']:
            self.result['componentResults'] = {}

        self.result['componentResults'][name] = {
            'status': status,
            'messages'   : {
                'info' : info,
                'error': error,
                'warn' : warn,
            },
        }

class BasePlugin(object):
    """
    Base class for all Python plugins
    """
    plugin = None
    result = None
    args   = None

    def __init__(self, plugin, **kwargs):
        """
        Set plugin parrent
        """
        self.plugin = plugin
        self.result = Result()

        self.args = kwargs

    def get_result(self):
        """
        Get and validate result
        Raise exception if it's not valid
        """
        return self.result.get_result()

    def execute(self, command, **kwargs):
        """
        Execute smoker.util.command.execute() with timeout (default 120 seconds)
        You shouldn't use anything else than this function from inside plugins!
        """
        # Set default timeout
        if not kwargs.has_key('timeout'):
            kwargs['timeout'] = self.plugin.get_param('Timeout', default=120)

        return smoker.util.command.execute(command, **kwargs)
