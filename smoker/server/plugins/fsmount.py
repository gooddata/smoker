#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Check file system mounts
Checks mount points for access and read/write

Parameters:
    Ignore  - regular expression for filtering ignored mount points (matches from the beginning of string)
    Types   - list of included filesystem types (default ext[234], fuse.glusterfs, nfs, nfs4, xfs, btrfs, reiserfs)
    Mounts  - list of mounts to check (default try to check all)
"""

import os
import random
import re
import logging

from smoker.server.plugins import BasePlugin

lg = logging.getLogger('smokerd.plugin.fsmount')

class Plugin(BasePlugin):
    def run(self):
        # Get parameters
        ignore = self.plugin.get_param('Ignore', default=None)
        types  = self.plugin.get_param('Types',
            default=['ext2', 'ext3', 'ext4', 'fuse.glusterfs', 'nfs', 'nfs4', 'xfs', 'btrfs', 'reiserfs'])
        check_mounts = self.plugin.get_param('Mounts', default=None)

        # Get all mounts
        try:
            mounts = self.get_mounts(ignore=ignore, types=types, mounts=check_mounts)
        except Exception as e:
            self.result.set_status('ERROR')
            self.result.add_error("Getting list of mounts failed: %s" % e)
            return self.result

        # No mounts found
        if not mounts:
            self.result.set_status('WARN')
            self.result.add_warn('No mounts found')
            return self.result

        for path, mount in mounts.iteritems():
            try:
                res = self.check_mount(path, mount)
                self.result.add_component(path, res['state'], **res['messages'])
            except Exception as e:
                self.result.add_component(path, 'ERROR', error=[str(e)])
                lg.exception(e)

        self.result.set_status()
        return self.result

    def check_mount(self, path, mount):
        """
        Check given mount
        """
        result = {
            'state' : 'OK',
            'messages': {
                'info'  : [],
                'error' : [],
                'warn'  : [],
            },
        }

        # Access check
        try:
            test = self.check_access(path)
            result['state'] = test['state']

            # Append messages
            for type, messages in test['messages'].iteritems():
                for msg in messages:
                    msg = 'Access: %s' % msg
                    result['messages'][type].append(msg)
        except Exception as e:
            result['state'] = 'ERROR'
            result['messages']['error'].append('Access: %s' % e)

        # Read/write check
        try:
            test = self.check_readwrite(path)

            # Update state
            if test['state'] == 'ERROR':
                result['state'] = 'ERROR'
            elif test['state'] == 'WARN' and result['state'] == 'OK':
                result['state'] = 'WARN'

            # Append messages
            for type, messages in test['messages'].iteritems():
                for msg in messages:
                    msg = 'Read/Write: %s' % msg
                    result['messages'][type].append(msg)
        except Exception as e:
            result['state'] = 'ERROR'
            result['messages']['error'].append('Read/Write: %s' % e)

        return result

    def check_access(self, path):
        """
        Check mount access
        """
        result = {
            'state' : 'OK',
            'messages': {
                'info'  : [],
                'error' : [],
                'warn'  : [],
            },
        }

        listing = os.listdir(path)
        result['messages']['info'].append("listed %d items in directory" % len(listing))

        return result

    def check_readwrite(self, path):
        """
        Check mount write and read
        """
        result = {
            'state' : 'OK',
            'messages': {
                'info'  : [],
                'error' : [],
                'warn'  : [],
            },
        }

        filename = random.randrange(0, 99999999, 8)
        filepath = ('%s/%s-smoker.tmp' % (path, filename)).replace('//', '/')

        # Write test
        try:
            fh = open(filepath, 'w')
            fh.write(str(filename))
            fh.flush()
            fh.close()
            result['messages']['info'].append('written string %s' % filename)
        except Exception as e:
            result['state'] = 'ERROR'
            result['messages']['error'].append('file write failed: %s' %e)
            return result

        # Read test
        try:
            fh = open(filepath, 'r')
            string = fh.read()
            fh.close()
            result['messages']['info'].append('read string %s' % string)
        except Exception as e:
            result['state'] = 'ERROR'
            result['messages']['error'].append('file read failed: %s' %e)
            pass
        finally:
            # Delete file
            try:
                os.unlink(filepath)
                result['messages']['info'].append('deleted file %s' % filepath)
            except Exception as e:
                result['state'] = 'ERROR'
                result['messages']['error'].append('file deletion failed: %s' %e)
                pass

        return result

    def get_mounts(self, ignore=None, types=[], mounts=[]):
        """
        Get mounted filesystems
        ignore - regular expressions for ignoring mount points (matches from the beginning of string)
        types  - filesystem types to look at
        mounts - return only specific mounts
        """
        result = {}
        with open('/proc/mounts', 'r') as fh:
            for line in fh:
                line = line.replace('\n', '')
                mount = line.split(' ')

                if mounts and mount[1] not in mounts:
                    continue
                elif types and mount[2] not in types:
                    continue
                elif ignore and re.match(ignore, mount[1]):
                    # Ignore mount point that matches regular expression
                    lg.debug('Ignoring mount point %s' % mount[1])
                    continue
                # do not check netapp snapshots (RO filesystems)
                elif '.snapshot' in mount[1]:
                    continue
                else:
                    result[mount[1]] = {
                        'device' : mount[0],
                        'mount'  : mount[1],
                        'type'   : mount[2],
                        'options': mount[3].split(','),
                        'dump'   : mount[4],
                        'pass'   : mount[5]
                    }

        return result
