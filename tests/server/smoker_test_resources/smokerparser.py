#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

import re

from smoker.server.parser import BaseParser


class Parser(BaseParser):
    def parse(self):
        info = re.findall('GoodData', self.stdout)[0]
        args = {
            'info': [info],
            'error': [],
            'warn': [],
        }
        self.result.add_component(name='Unit tests', status='OK', **args)
        self.result.set_status()
        return self.result
