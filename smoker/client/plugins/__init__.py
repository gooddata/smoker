# -*- coding: utf-8 -*-
# Copyright (C) 2007-2015, GoodData(R) Corporation. All rights reserved
#
# Example plugin:
#
# from smoker.client.plugins import SpecificArgument, HostDiscoveryPluginBase
#
#
# class HostDiscoveryPlugin(HostDiscoveryPluginBase):
#     """
#     This is an example without any real world usability
#     """
#     arguments = [
#         SpecificArgument(
#             '-x',
#             '--example',
#             **{'dest': 'example',
#                'help': 'Example parameter for host discovery'}
#         ),
#         SpecificArgument(
#             '-y',
#             '--example_prefix',
#             **{'dest': 'prefix',
#                'help': 'Another example for host discovery'}
#         )
#     ]
#
#     def get_hosts(self, args):
#         if not args.example:
#             return []
#         if not args.prefix:
#             return [args.example]
#         return ['%s-%s' % (args.prefix, args.example)]


class SpecificArgument(object):
    """
    Argparse argument to be added to the smoker CLI specific to this plugin
    """
    def __init__(self, short, long, **kwargs):
        if short and long:
            self.args = [short, long]
        elif short:
            self.args = [short]
        else:
            self.args = [long]
        self.kwargs = kwargs


class HostDiscoveryPluginBase(object):
    """
    Host discovery plugin interface
    Inherit from this class when creating a host discovery plugin
    """
    # List of Specific Argument instances to be added
    # to argparse.ArgumentParser
    arguments = []

    def get_hosts(self, args):
        """
        Override this method in your plugin

        :return: discovered hosts
        """
        return []
