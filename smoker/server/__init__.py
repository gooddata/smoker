#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import os
import sys


def redirect_standard_io(config):
    """
    :param config: configuration with filenames for I/O
    :type cofig: dict with keys 'stdin', 'stdout' and 'stderr'
    """
    sys.stdout.flush()
    sys.stderr.flush()

    si = file(config['stdin'], 'r')
    so = file(config['stdout'], 'a+')
    se = file(config['stderr'], 'a+', 0)

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
