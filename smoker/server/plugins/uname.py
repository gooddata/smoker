#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Example plugin that will return
basic informations about system
"""

import os

from smoker.server.plugins import BasePlugin

class Plugin(BasePlugin):
    def run(self):
        # Plugin can access it's parrent
#       self.plugin.params (or get_param() method)
#       self.plugin.result

        uname = os.uname()
        msg = ' '.join(uname)

        self.result.set_status('OK')
        self.result.add_info(msg)

        return self.result
