#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import glob
import logging
import os
import signal
import sys
import time
import yaml

from smoker.server.plugins import PluginManager
from smoker.server.restserver import RestServer

lg = logging.getLogger('smokerd.daemon')


class Smokerd(object):
    """
    Main entrance for smokerd
    """

    conf = {}

    # ThreadedHTTPServer instance
    server = None

    # PluginManager instance
    pluginmgr = None

    def __init__(self, **kwargs):
        """
        Initialize smokerd
         * load submitted arguments
         * load config
         * catch SIGINT/SIGTERM
        """
        # Load user-supplied arguments and config file
        # args have to be dictionary
        self.conf = kwargs

        if 'config' not in kwargs:
            lg.info("Config argument not submitted, default config file will be used!")
            self.conf['config'] = '/etc/smokerd/smokerd.yaml'

        self.conf_dirs = [os.path.dirname(self.conf['config'])]

        self._load_config()

    def _yaml_include(self, loader, node):
        """
        Include another yaml file from main file
        This is usually done by registering !include tag
        """
        filepath = node.value
        if not os.path.exists(filepath):
            for dir in self.conf_dirs:
                filepath = os.path.join(dir, node.value)
                if os.path.exists(filepath):
                    break

        self.conf_dirs.append(os.path.dirname(filepath))
        try:
            with open(filepath, 'r') as inputfile:
                return yaml.load(inputfile)
        except IOError as e:
            lg.error("Can't include config file %s: %s" % (filepath, e))
            raise

    def _yaml_include_dir(self, loader, node):
        """
        Include another yaml file from main file
        This is usually done by registering !include tag
        """
        if not os.path.exists(node.value):
            return

        yamls = glob.glob(os.path.join(node.value, '*.yaml'))
        if not yamls:
            return

        content = '\n'

        for file in yamls:
            plugin, _ = os.path.splitext(os.path.basename(file))
            content += '    %s: !include %s\n' % (plugin, file)

        return yaml.load(content)

    def _load_config(self):
        """
        Load specified config file
        """
        try:
            with open(self.conf['config'], 'r') as fp:
                config = fp.read()
        except IOError as e:
            lg.error("Can't read config file %s: %s" % (self.conf['config'], e))
            raise

        # Register include constructors
        yaml.add_constructor('!include_dir', self._yaml_include_dir)
        yaml.add_constructor('!include', self._yaml_include)

        try:
            conf = yaml.load(config)
        except Exception as e:
            lg.error("Can't parse config file %s: %s" % (self.conf['config'], e))
            raise
        finally:
            fp.close()

        # Store parameters but don't overwite
        # those submitted by command line
        for key, value in conf.iteritems():
            if self.conf.has_key(key):
                # User has submitted own parameter,
                # use that instead of config one
                lg.debug("Using parameter %s from user, ignoring config file value" % key)
            else:
                self.conf[key] = value

    def run(self):
        """
        Run daemon
         * change effective uid/gid
         * start thread for each check
         * start webserver
        """
        lg.info("Starting daemon")

        # Change effective UID/GID
        if self.conf.has_key('uid') and self.conf.has_key('gid'):
            if os.geteuid != self.conf['uid'] and os.getegid != self.conf['gid']:
                try:
                    os.setegid(self.conf['gid'])
                    os.seteuid(self.conf['uid'])
                except TypeError as e:
                    lg.error("Config parameters uid/gid have to be integers: %s" % e)
                except OSError as e:
                    lg.error("Can't switch effective UID/GID to %s/%s: %s" % (self.conf['uid'], self.conf['gid'], e))
                    lg.exception(e)
                    self._shutdown(exitcode=1)
        else:
            lg.info("Not changing effective UID/GID, keeping %s/%s" % (os.geteuid(), os.getegid()))

        if not isinstance(self.conf['bind_port'], int):
            lg.error("Config parameter bind_port has to be integer")

        # Initialize plugin manager
        config = {}

        for key in ['plugins', 'templates', 'actions']:
            try:
                config[key] = self.conf[key]
            except KeyError as e:
                lg.warn("Config section not found: %s" % e)

        # Check we have some plugins configured
        if not config['plugins']:
            lg.error('No configured plugins')
            self._shutdown(exitcode=1)

        try:
            self.pluginmgr = PluginManager(**config)
        except Exception as e:
            lg.error("Can't initialize PluginManager")
            lg.exception(e)
            self._shutdown(exitcode=1)

        try:
            self.pluginmgr.start()
        except Exception as e:
            lg.error("Can't start PluginManager")
            lg.exception(e)
            self._shutdown(exitcode=1)

        lg.info("Starting webserver on %(bind_host)s:%(bind_port)s" % self.conf)
        try:
            self.server = RestServer(self.conf['bind_host'], self.conf['bind_port'], self)
            self.server.start()
        except Exception as e:
            lg.error("Can't start HTTP server: %s" % e)
            lg.exception(e)
            self._shutdown(exitcode=1)

        # Catch SIGINT and SIGTERM if supported
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._shutdown)

        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._shutdown)
        # API server loop now runs in a separate process and we don't want
        # to terminate to keep an instance of pluginmanager

        self._watchdog()

    def _watchdog(self):
        lg.debug("Starting the smoker watchdog")

        while True:
            if not self.server.is_alive():
                lg.error("REST API server is dead")
                self._restart_api_server()
                lg.info("restarted the REST API server")

            for plugin in self.pluginmgr.plugins.values():
                if not plugin.is_alive():
                    lg.error("Plugin %s is dead" % plugin.name)
                    self.pluginmgr.restart_plugin(plugin.name)
                    # need to restart the REST server so it has reference to
                    # the new plugin instance
                    self._restart_api_server()
            time.sleep(10)

    def _restart_api_server(self):
        self.server.terminate()
        self.server.join()
        self.server = RestServer(self.conf['bind_host'], self.conf['bind_port'], self)
        self.server.start()

    def stop(self):
        """
        Kill running daemon

        Use sys.exit() here instead of self._shutdown(), because it's executed from separate process
        """
        if not os.path.isfile(self.conf['pidfile']):
            lg.error("PID file doesn't exist! Daemon not running?")
            sys.exit(1)
        fp = open(self.conf['pidfile'], 'r')
        pid = fp.read()
        fp.close()
        lg.info("Killing process %s" % pid)
        os.kill(int(pid), signal.SIGTERM)

    def daemonize(self):
        """
        Daemonize and run daemon
        Use double-fork magic to do that

        Use sys.exit() here instead of self._shutdown() because we don't have running
        daemon to shutdown in this function
        """
        # Check PID file
        if os.path.isfile(self.conf['pidfile']):
            lg.error("PID file %s already exists" % self.conf['pidfile'])
            sys.exit(1)

        # Unix double-fork magic
        pid = os.fork()
        if pid:
            sys.exit(0)

        os.chdir('/')
        os.setsid()
        os.umask(0)

        pid = os.fork()
        if pid:
            sys.exit(0)

        # Ensure that directories for stdout and stderr logging
        # exists or create them
        for log in ['stdout', 'stderr', 'stdin']:
            path = os.path.dirname(self.conf[log])
            if not os.path.exists(path):
                os.mkdir(path)

        # Redirect standard I/O
        sys.stdout.flush()
        sys.stderr.flush()
        try: 
            si = file(self.conf['stdin'], 'r')
            so = file(self.conf['stdout'], 'a+')
            se = file(self.conf['stderr'], 'a+', 0)
        except Exception as e:
            lg.error("Can't open configured output: %s" % e)
            lg.exception(e)
            sys.exit(1)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Save PID into pidfile
        try:
            fh = open(self.conf['pidfile'], 'w')
            fh.write(str(os.getpid()))
            fh.flush()
            fh.close()
        except Exception as e:
            lg.error("Can't write PID into pidfile: %s" % e)
            sys.exit(1)

        try:
            self.run()
        except Exception as e:
            # On exception, try to shutdown and log
            self._shutdown(exitcode=1)
            lg.exception(e)

    def _shutdown(self, signum=None, frame=None, exitcode=0, exception=False):
        """
        Shutdown smoker daemon (internal use)
        exitcode - exit code number (default 0)
        signum, frame - used by signal handler
        exception - if True, raise on exception, otherwise just log it and pass
        """
        # Ignore if we are already stopping
        if self.pluginmgr and self.pluginmgr.stopping:
            return

        lg.info("Shutting down")
        try:
            # Shutdown webserver
            if self.server:
                self.server.terminate()
                self.server.join()

            # Shutdown pluginmanager and all plugins
            if self.pluginmgr:
                self.pluginmgr.stop()

            # Remove PID file if exists
            if os.path.isfile(self.conf['pidfile']):
                os.remove(self.conf['pidfile'])
        except Exception as e:
            lg.exception(e)
            if exception:
                raise

        sys.exit(exitcode)
