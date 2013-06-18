#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Parser varnishparser is used to parse
output from varnishadm 'debug.health'

If output can't be parsed, it will raise exception
and default result output will be used
"""

import re

from smoker.server.parser import BaseParser


class Parser(BaseParser):
    def parse(self):
        """
        If we got stdout, parse it and return result.
        Else return Exception that is handled by smokerd.
        """
        backends = re.findall("Backend\ (.*)\ is\ (.*)\n.*\nAverage responsetime of good probes:\ (.*)", self.stdout)

        if not backends:
            raise Exception("No backends found or output can't be parsed!")

        for backend in backends:
            name    = backend[0]
            state   = backend[1]
            restime = float(backend[2])

            args = {
                'info' : [],
                'error': [],
                'warn' : [],
            }

            # Check backend state
            if state == 'Healthy':
                # Check backend response time
                if restime > 0.5:
                    state = 'WARN'
                    args['warn'].append('Response time: %s' % restime)
                else:
                    state = 'OK'
                    args['info'].append('Response time: %s' % restime)
            else:
                state = 'ERROR'
                args['error'].append('State: %s' % backend[1])

            self.result.add_component(name, state, **args)

        self.result.set_status()

        return self.result
