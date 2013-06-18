#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

from smoker.server.plugins import Result

class BaseParser(object):
    """
    Base class for all parsers
    """
    stdout = None
    stderr = None
    result = None

    def __init__(self, stdout, stderr):
        """
        Set stdout and stderr
        """
        self.stdout = stdout
        self.stderr = stderr
        self.result = Result()

    def get_result(self):
        """
        Get result
        """
        return self.result.get_result()
