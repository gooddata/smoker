# -*- coding: utf-8 -*-
# Copyright (C) 2007-2014, GoodData(R) Corporation. All rights reserved

"""
Try to connect to given set of host, port and report status.

Parameters:
    Connections - Dictionary of [host, port] dict to try to connect to, example
                  [ ['icinga.mydomain',5556], ['myhost.mydomain',80 ] ]
    Timeout - timeout for requests, default 10 seconds

"""

from smoker.server.plugins import BasePlugin

import logging
lg = logging.getLogger('smokerd.plugin.testconnection')

import threading
import socket


class Plugin(BasePlugin):
    url = None
    params = None
    suite = None
    timeout = None

    def run(self):
        """
        Run plugin
         * get parameters and set defaults
         * run ConnectionCheck for all host, port combinations in parallel
        """
        # Get parameters
        self.addresses = self.plugin.get_param('Connections', [])
        self.timeout = self.plugin.get_param('Timeout', 10)

        # Defaults
        if not self.addresses and not isinstance(self.addresses, dict):
            raise Exception('Parameter Connections have to be dictionary of '
                            '(host, port) tuples')

        for conn in self.addresses:
            if (not (isinstance(conn, tuple) or isinstance(conn, list)) and
                    len(conn) != 2):
                raise Exception(
                    "Every parameter has to be a [host, port] list")

        threads = []
        for conn in self.addresses:
            t = ConnectionCheck((conn[0], conn[1]), self.timeout)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        err = []
        for t in threads:
            err.extend(t.err)
        status = "OK"
        if err:
            status = "ERROR"
        self.result.add_component('Connection', status, error=err)
        self.result.set_status()
        return self.result


class ConnectionCheck(threading.Thread):
    """
    Opens socket to supplied address and check the return status,
    leaving results in self.err and self.info array.
    """
    def __init__(self, address, timeout):
        threading.Thread.__init__(self)
        self.timeout = timeout
        self.address = address
        self.err = []
        self.info = []

    def run(self):
        try:
            s = socket.create_connection(self.address, self.timeout)
            s.close()
            self.info.append("Host: %s" % self.address[0])
        except (socket.herror, socket.gaierror) as e:
            self.err.append(
                "Host: %s resolving error: %s" % (self.address[0], e))
        except socket.timeout as e:
            self.err.append(
                "Host: %s, port: %s connection timeout" % self.address)
        except socket.error as e:
            self.err.append("Host: %s, port: %s, Socket error: %s" %
                            (self.address[0], self.address[1], e))
        except Exception as e:
            lg.exception()
            self.err.append(
                "Host: %s, Unknown exception: %s" % (self.address[0], e))
