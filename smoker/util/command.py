#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

"""
Module for various command executions
"""

import subprocess
import threading
import os
import psutil
import atexit
import datetime
import logging
import time
lg = logging.getLogger(__name__)

def execute(command, timeout=None, **kwargs):
    """
    Execute command, wrapper for Command class

    :param command: list for non-shell execution, string for shell execution
    :param timeout: timeout in seconds
    :param kwargs: keyword arguments to pass to subprocess.Popen

    :rtype: tuple (stdout, stderr, retval)
    """
    cmd = Command(command, **kwargs)
    return cmd.run(timeout)

def signal_ptree(pid, signal=15):
    """
    Send signal to whole process tree
    By default send SIGTERM (15).
    If process doesn't exist, just pass

    :param pid: process id
    :param signal: signal number, send SIGTERM (15) by default
    """
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        # Process could be already dead, just skip killing children
        return

    # Get children process tree (psutil 0.4.1 doesn't support recursive=True)
    children = get_ptree(process)

    lg.info('Sending signal to process tree: signal=%s pid=%s process=%s children=%s' % (signal, process.pid, process.name, len(children)))

    if children:
        # Children have to be from bottom to top list
        for child in children:
            try:
                lg.info('Sending signal to child process: signal=%s pid=%s process=%s' % (signal, child.pid, child.name))
                os.kill(child.pid, signal)
            except OSError as e:
                if e.errno == 3:
                    # No such process - it's ok, it could be dead already
                    lg.debug('Children process does not exist: pid=%s process=%s' % (child.pid, child.name))
                    continue

    # Kill parent
    try:
        lg.info('Sending signal to parent process: signal=%s pid=%s process=%s' % (signal, process.pid, process.name))
        os.kill(process.pid, signal)
    except OSError as e:
        if e.errno == 3:
            # No such process - it's ok, it could die with it's children
            lg.debug('Parent process does not exist: pid=%s process=%s' % (process.pid, process.name))
            pass

def get_ptree(process):
    """
    Get process children recursive.
    Used for compatibility with psutil 0.4.1, newer versions supports recursive=True parameter.
    Given process isn't included in returned list.
    Process tree list is reversed, so first are children from bottom to top.

    :param process: psutil.Process instance or uid
    :rtype: list (psutil.Process)
    """
    if not isinstance(process, psutil.Process):
        process = psutil.Process(process)

    result = []
    children = process.get_children()
    if children:
        for child in children:
            if child.get_children():
                result.extend(get_ptree(child))
                result.append(child)
            else:
                result.append(child)
    return result

def _proc_cleanup(pid):
    """
    Try to cleanup process tree

    :param pid: process id
    """
    if pid:
        try:
            process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return

        signal_ptree(process)
        if process.is_running():
            # Still running - wait 1 second before sending SIGKILL
            time.sleep(1)
            signal_ptree(process, 9)

def _register_cleanup(pid):
    """
    Register cleanup function for given process id

    :param pid: process id
    """
    lg.debug("Registering cleanup for pid %s" % pid)
    atexit.register(_proc_cleanup, pid)

def _unregister_cleanup(pid):
    """
    Unregister cleanup function for given process id

    :param pid: process id
    """
    lg.debug("Unregistering cleanup for pid %s" % pid)

    # Newer atexit has unregister, but we want to be compatible
    for handler in atexit._exithandlers:
        (func, args, kwargs) = handler
        if func == _proc_cleanup and args == (pid,):
            atexit._exithandlers.remove(handler)

class Command(object):
    """
    Class for command executions
    """
    def __init__(self, command, **kwargs):
        """
        Initialize instance

        :param command: list for non-shell execution, string for shell execution
        :param kwargs: keyword arguments to pass to subprocess.Popen
        """
        self.command = command

        self.process = None

        self.stdout = None
        self.stderr = None
        self.returncode = None

        self._exception = None

        # Default arguments
        popen_args = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'bufsize': 0
        }

        # We want to pass shell=True argument if we have string command
        if isinstance(command, basestring):
            popen_args['shell'] = True

        # Merge our arguments and supplied ones in kwargs
        self.kwargs = dict(popen_args, **kwargs)

    def __repr__(self):
        """
        Instance name
        """
        return '<Command \'%s\'>' % self.command

    def run(self, timeout=None, timeout_sigterm=3, timeout_sigkill=5):
        """
        Run command with given timeout.
        Return tuple of stdout, stderr strings and retval integer.

        :param timeout: if command doesn't exit in given timeout, kill the process (default no timeout)
        :param timeout_sigterm: wait approximately given seconds after sending SIGTERM before sending SIGKILL (default 3)
        :param timeout_sigkill: wait approximately given seconds after sending SIGKILL before considering thread as deadlocked (default 5)

        :rtype: tuple (stdout, stderr, retval)
        """
        def target():
            """
            Thread target function
            """
            try:
                self.process = subprocess.Popen(self.command, **self.kwargs)
                # Register cleanup function to avoid running processes after program exit
                _register_cleanup(self.process.pid)
                self.stdout, self.stderr = self.process.communicate()

                # Remove unwanted leading/trailing whitespaces from output
                # Force stdout/stderr to be string if it's empty
                self.stdout = self.stdout.strip() if self.stdout else ''
                self.stderr = self.stderr.strip() if self.stderr else ''

                self.returncode = self.process.returncode
            except Exception as e:
                self._exception = e
                return e

        # Run thread with command and wait
        thread = threading.Thread(target=target)
        lg.debug("Executing command: command='%s' %s"
            % (self.command, ' '.join('%s=%s' % (a, b) for a, b in self.kwargs.iteritems())))
        time_start = datetime.datetime.now()
        thread.start()

        if timeout:
            thread.join(timeout)

            # Thread still alive? Timeout!
            if thread.is_alive():
                # Terminate process and wait 3 seconds
                signal_ptree(self.process.pid)
                thread.join(timeout_sigterm)

                if thread.is_alive():
                    # Thread still alive -> send SIGKILL
                    signal_ptree(self.process.pid, signal=9)
                    thread.join(timeout_sigkill)

                    if thread.is_alive():
                        # Thread still alive -> deadlock
                        # Unregister cleanup function in case that process would die to avoid killing re-used PID
                        _unregister_cleanup(self.process.pid)
                        raise ThreadDeadlock("Process %s deadlocked thread %s" % (self.process.pid, thread.name))
                # Process is no running, unregister cleanup and raise Timeout exception
                _unregister_cleanup(self.process.pid)
                raise ExecutionTimeout("Execution timeout after %s seconds" % timeout)
        else:
            # No timeout applied.. only insane people should do this.
            thread.join()

        # Handle exception from thread
        if self._exception:
            # It means that process is not running, so unregister cleanup and re-raise exception
            _unregister_cleanup(self.process.pid)
            raise self._exception

        lg.debug("Command execution done: time=%s returncode=%s" %
                 ((datetime.datetime.now() - time_start).seconds, self.returncode))

        # We are successfully done, unregister cleanup to avoid killing re-used PID uppon server shutdown
        _unregister_cleanup(self.process.pid)
        return (self.stdout, self.stderr, self.returncode)

## Exceptions
class ExecutionTimeout(Exception):
    """
    Raise timeout exception
    """
    pass

class ThreadDeadlock(Exception):
    """
    Process can't be killed, caused deadlock of executing thread
    """
    pass
