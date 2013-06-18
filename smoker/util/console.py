#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

"""
Module with various console utils
"""

import sys
import fcntl, termios, struct

def get_terminal_size():
    """
    Get terminal width and height
    Return (width, height) tuple
    """
    h, w, hp, wp = struct.unpack('HHHH',
        fcntl.ioctl(0, termios.TIOCGWINSZ,
            struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h

def is_interactive_shell():
    """
    Try to guess if current shell is interactive
    Return bool
    """
    return sys.__stdout__.isatty()