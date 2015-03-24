#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Initialize GDC logging

Initialize:
import smoker.logger as logger
import logging
logger.init()
lg = logging.getLogger('application')
lg.info("Logger loaded")

Usage:
import logging
lg = logging.getLogger('application')
"""

import logging
import logging.config
import logging.handlers
import os
from smoker.logger.level_handler import LevelHandler

lg = None


def disable_console_logging(logger):
    handlers = logger.handlers
    for handler in handlers:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)
        if logger.parent:
            disable_console_logging(logger.parent)


# Initialize logging
def init(name='', level=logging.WARN, syslog=True, console=True,
         config_file=''):
    global lg

    if os.path.exists(config_file):
        logging.config.fileConfig(config_file)

    lg = logging.getLogger(name)
    lg.setLevel(level)

    if os.path.exists(config_file):
        if not console:
            disable_console_logging(lg)
        return lg

    if console:
        lg_console = LevelHandler()
        lg_console.setFormatter(
            logging.Formatter('%(levelname)s: %(message)s'))

        lg.addHandler(lg_console)

    if syslog:
        lg_syslog = logging.handlers.SysLogHandler(address='/dev/log')
        lg_syslog.setFormatter(
            logging.Formatter('%(name)-9s %(levelname)-8s %(message)s'))

        lg.addHandler(lg_syslog)

    return lg
