#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

import sys

EXIT_OK = 0
EXIT_WARNING  = 1
EXIT_CRITICAL = 2
EXIT_UNKNOWN  = 3

def exit_critical(msg):
    print "CRITICAL: %s" % msg
    sys.exit(EXIT_CRITICAL)

def exit_warning(msg):
    print "WARNING: %s" % msg
    sys.exit(EXIT_WARNING)

def exit_unknown(msg):
    print "UNKNOWN: %s" % msg
    sys.exit(EXIT_UNKNOWN)

def exit_ok(msg):
    print "OK: %s" % msg
    sys.exit(EXIT_OK)
