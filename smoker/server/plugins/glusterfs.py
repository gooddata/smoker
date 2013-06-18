#!/usr/bin/env python
# -*- coding: utf8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Plugin to get overall GlusterFS status
This will check only up to 50 gluster peers

Parameters:
    Volume  - volume to run mount/unmount test. If it's not set, mount test won't be executed.
"""

import logging
lg = logging.getLogger('smokerd.plugin.glusterfs')

from smoker.server.plugins import BasePlugin
from xml.dom import minidom
import subprocess
import os
import tempfile
import random
import time

class Plugin(BasePlugin):
    def run(self):
        """
        Main entrance
         * check peers status
         * check volumes status
         * try to mount and unmount volume
        """

        volume = self.plugin.get_param('Volume')

        try:
            self.check_peers()
        except Exception as e:
            self.result.add_component('Peers', 'ERROR', error=["Can't check peers: %s" % e])
            lg.exception(e)

        try:
            self.check_volumes()
        except Exception as e:
            self.result.add_component('Volumes', 'ERROR', error=["Can't check volumes: %s" % e])
            lg.exception(e)

        if volume:
            try:
                self.mount(volume)
            except Exception as e:
                self.result.add_component('Mount', 'ERROR', error=["Can't mount volume: %s" % e])
                lg.exception(e)

        self.result.set_status()
        return self.result

    def check_peers(self):
        """
        Check peers status
        and add component result
        """
        peers = self.getPeersStatus()
        status = 'OK'
        messages = {
            'info' : [],
            'error': [],
            'warn' : [],
        }

        for host, peer in peers.iteritems():
            if peer['connected'] == True:
                messages['info'].append('Peer %s is healthy: %s (Connected)' % (host, peer['status']))
            else:
                messages['error'].append('Peer %s is not healthy: %s (Disconnected)' % (host, peer['status']))
                status = 'ERROR'

        self.result.add_component('Peers', status, **messages)

    def check_volumes(self):
        """
        Check volumes status
        and add component result
        """
        volumes = self.getVolumesStatus()
        status = 'OK'
        messages = {
            'info' : [],
            'error': [],
            'warn' : [],
        }

        # Less than 1 volume?
        if len(volumes) < 1:
            messages['error'].append("No configured volumes found")
            status = 'ERROR'

        # Check status of each volume
        for vol, nodes in volumes.iteritems():
            if nodes['status'] != 1:
                # Get broken nodes
                failed = []
                for node, status in nodes.iteritems():
                    if node != 'status' and status != 1:
                        failed.append(node)
                
                messages['error'].append("Volume %s is not healthy (failed nodes: %s)" % (vol, ', '.join(failed)))
                status = 'ERROR'
            else:
                messages['info'].append("Volume %s is healthy" % vol)

        self.result.add_component('Volumes', status, **messages)

    def getPeersStatus(self):
        """
        Get status of gluster peers

        Return dictionary of peers and their status:
        peers = {
            'gluster01': {
                'connected' : 1,
                'status' : 'Peer rejected',
            }
        }
        """
        peers = {}
        stdout, stderr, retval = self.execute('/usr/sbin/gluster peer status --xml', stderr=subprocess.STDOUT)

        try:
            xml = minidom.parseString(stdout)
        except Exception as e:
            # eg. No peers present
            raise Exception(stdout)

        for i in range(50):
            try:
                hostname = xml.getElementsByTagName('friend%d.hostname' % i)[0].toxml().replace('<friend%d.hostname>' % i, '').replace('</friend%d.hostname>' % i, '')
                connected   = xml.getElementsByTagName('friend%d.connected' % i)[0].toxml().replace('<friend%d.connected>' % i, '').replace('</friend%d.connected>' % i, '')
                status = xml.getElementsByTagName('friend%d.state' % i)[0].toxml().replace('<friend%d.state>' % i, '').replace('</friend%d.state>' % i, '')
            except:
                continue

            # Update connected status
            if int(connected) == 1:
                connected = True
            else:
                connected = False

            peers[hostname] = {
                'connected'  : connected,
                'status': status,
            }

        return peers

    def getVolumesStatus(self):
        """
        Get status for all volumes

        Return dictionary with status of every volume:
        status = {
            'Volume' : {
                'gluster01' : 1,
                'gluster01' : 1,
                'status'    : 1,
            }
        }
        """
        status  = {}
        volumes = self.getVolumes()
        for vol in volumes:
            status[vol] = self.getStatus(vol)

        return status

    def getVolumes(self):
        """
        Get list of available volumes
        """
        volumes = []
        stdout, stderr, retval = self.execute('/usr/sbin/gluster volume list', stderr=subprocess.STDOUT)
        for vol in stdout.split('\n'):
            vol = vol.replace('\n', '')
            if vol:
                volumes.append(vol)
        return volumes

    def getStatus(self, volume):
        """
        Get volume status

        Return dictionary with status of every node and overall status:
        status = {
            'gluster01' : 1,
            'gluster02' : 1,
            'status'    : 1,
        }
        """
        volStat = {
            'status' : 1,
        }

        ret = 1
        tries = 0
        retry = 5
        while ret != 0 and tries <= retry:
            stdout, stderr, retval = self.execute('/usr/sbin/gluster volume status %s --xml' % volume, stderr=subprocess.STDOUT)

            try:
                xml = minidom.parseString(stdout)
            except Exception as e:
                raise Exception("Unexpected output from gluster volume status %s --xml: %s" % (volume, stdout))

            # Can't get volume info, sleep for a while and try it again (only one command of this type can be run on cluster)
            ret = int(xml.getElementsByTagName('opRet')[0].toxml().replace('<opRet>', '').replace('</opRet>', ''))
            tries += 1
            time.sleep(random.uniform(0, 1))

        if ret != 0:
            raise Exception("Can't get data for %s after %d retries" % (volume, retry))

        nodes = xml.getElementsByTagName('node')

        for node in nodes:
            hostname = node.getElementsByTagName('hostname')[0].toxml().replace('<hostname>', '').replace('</hostname>', '')
            status   = int(node.getElementsByTagName('status')[0].toxml().replace('<status>', '').replace('</status>', ''))
            volStat[hostname] = status

            # Set failed status for volume
            if status != 1 and volStat['status'] == 1:
                volStat['status'] = 0

        return volStat

    def mount(self, volume):
        tmp = tempfile.mkdtemp()

        status = 'OK'
        messages = {
            'info' : [],
            'error': [],
            'warn' : [],
        }

        try:
            stdout, stderr, retval = self.execute('/bin/mount -t glusterfs localhost:%s %s' % (volume, tmp), stderr=subprocess.STDOUT)

            if retval:
                messages['error'].append(stderr)
                status = 'ERROR'
            else:
                # Unmount
                stdout, stderr, retval = self.execute('/bin/umount %s' % tmp, stderr=subprocess.STDOUT)

                if retval:
                    messages['error'].append(stderr)
                    status = 'ERROR'
            
            self.result.add_component('Mount', status, **messages)
        finally:
            os.rmdir(tmp)
