#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import argparse
import logging
import sys

from smoker.server.daemon import Smokerd
import smoker.logger


def main():
    parser = argparse.ArgumentParser(description='Smoke testing daemon')
    parser.add_argument('-c', '--config', dest='config', default='/etc/smokerd/smokerd.yaml', help="Config file to use (default /etc/smokerd/smokerd.yaml)")
    parser.add_argument('-p', '--pidfile', dest='pidfile', default='/var/run/smokerd.pid', help="PID file to use (default /var/run/smokerd.pid)")
    parser.add_argument('-fg', '--foreground', dest='foreground', action='store_true', help="Don't fork into background")
    parser.add_argument('--stop', dest='stop', action='store_true', help="Stop currently running daemon")
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help="Be verbose")
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help="Debug output")
    args = parser.parse_args()

    # Don't log into console if we are going to background
    if not args.foreground:
        lg = smoker.logger.init(console=False)
    else:
        lg = smoker.logger.init()

    if args.verbose:
        lg.setLevel(logging.INFO)

    if args.debug:
        lg.setLevel(logging.DEBUG)

    daemon = Smokerd(
        config  = args.config,
        pidfile = args.pidfile
    )

    if args.stop:
        daemon.stop()
        sys.exit(0)

    if args.foreground:
        daemon.run()
    else:
        daemon.daemonize()

if __name__ == '__main__':
    main()
