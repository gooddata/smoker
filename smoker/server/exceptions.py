#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Module providing exceptions for smokerd
"""

# PluginManager exceptions
class TemplateNotFound(Exception):
    """
    Can't find template
    """
    pass

class NoTemplatesConfigured(Exception):
    """
    There are no configured templates
    """
    pass

class BasePluginTemplateNotFound(Exception):
    """
    BasePlugin template is not found
    """
    pass

class NoRunningPlugins(Exception):
    """
    No plugins loaded
    """
    pass

class ActionNotFound(Exception):
    """
    Can't find action
    """
    pass

class NoActionsConfigured(Exception):
    """
    There are no configured actions
    """
    pass

class InvalidArgument(Exception):
    """
    Invalid argument
    """
    pass

class ValidationError(Exception):
    """
    Error during validation
    """
    pass

class NoSuchPlugin(Exception):
    """
    Plugin does not exists
    """
    pass

class NoPluginsFound(Exception):
    """
    No plugins was found by given name(s) or filter
    """

# Plugin exceptions
class PluginExecutionError(Exception):
    """
    Plugin execution failed
    eg. command not found, etc.
    """
    pass

class PluginExecutionTimeout(Exception):
    """
    Plugin execution timeouted
    """
    pass

class PluginMalformedOutput(Exception):
    """
    Plugin output was not recognized
    eg. malformed JSON, missing status in output
    """
    pass

class InvalidConfiguration(Exception):
    """
    Not valid configuration parameters
    or their combination supplied
    """
    pass

# Httpserver exceptions
class InProgress(Exception):
    """
    Process run is still in progress
    """
    pass
