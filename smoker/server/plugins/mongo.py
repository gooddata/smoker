#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012, GoodData(R) Corporation. All rights reserved

"""
Connect to Mongo, test it's status

Parameters:
    Host    - host to connect to (default localhost)
    Port    - port to connect to (required)
    ValidateCollections - validate collections or not (default False)
    EmptyCollections    - if true, warn on empty collections (default False)
    ReplicaSet  - replica set to use (default text)
"""

import logging

from smoker.server.plugins import BasePlugin
lg = logging.getLogger('smokerd.plugin.mongo')

import datetime
import pymongo

class Plugin(BasePlugin):
    connection = None
    validate   = False
    host  = None
    port  = None
    empty = False
    replicaset = None

    def run(self):
        # Get parameters
        self.host = self.plugin.get_param('Host', 'localhost')
        self.port = self.plugin.get_param('Port', 27017)
        self.validate_collections = self.plugin.get_param('ValidateCollections')
        self.empty_collections = self.plugin.get_param('EmptyCollections')
        self.replicaset = self.plugin.get_param('ReplicaSet', 'test')

        # Define component checks
        checks = [
            { 'Connection' : self.check_connection },
            { 'Members' : self.check_members },
            { 'Collections' : self.check_collections },
            { 'Record' : self.check_record }
        ]

        # Check components
        for item in checks:
            for check, check_function in item.iteritems():
                try:
                    res = check_function()
                    self.result.add_component(check, res['state'], **res['messages'])
                except Exception as e:
                    self.result.add_component(check, 'ERROR', error=[str(e)])
                    lg.exception(e)

        self.result.set_status()
        return self.result

    def check_record(self):
        """
        Try to write and read from collection
        """
        result = {
            'state' : 'OK',
            'messages': {
                'info'  : [],
                'error' : [],
                'warn'  : [],
            }
        }

        # Use database test
        db = self.connection['test']

        # Use collection test
        collection = db.test

        # Write new post
        try:
            id = collection.insert({
                'name' : 'John Doe',
                'text' : 'Testing record',
                'date' : datetime.datetime.now()
            })
            result['messages']['info'].append("Inserted record with id %s" % id)
        except Exception as e:
            result['messages']['error'].append("Inserting record into collection failed: %s" % e)
            result['state'] = 'ERROR'
            return result

        # Read our post
        post = collection.find_one()
        if post:
            result['messages']['info'].append("Found our record: %s" % post)
        else:
            result['messages']['error'].append("Inserted record not found!")
            result['state'] = 'ERROR'

        # Empty collection
        try:
            collection.remove()
            result['messages']['info'].append("Deleted everything from collection test")
        except Exception as e:
            result['messages']['error'].append("Can't delete everything from collection test: %s" % e)
            result['state'] = 'ERROR'

        return result

    def check_collections(self):
        """
        Check collections in all databases
        """
        result = {
            'state' : 'OK',
            'messages' : {
                'info' : [],
                'error': [],
                'warn' : [],
            }
        }

        databases = self.connection.database_names()

        if not databases:
            result['state'] = 'WARN'
            result['messages']['warn'].append('No databases found')

        # Check each database and it's collections
        for database in databases:
            db = self.connection[database]
            collections = db.collection_names()

            if self.empty_collections and not collections:
                # No collections in database - WARN and continue
                if database == 'local':
                    # ignore on database local - it's OK to be empty
                    if result['state'] not in ['ERROR', 'WARN']:
                        result['state'] = 'OK'
                    result['messages']['info'].append('Database %s: no collections found but it is expected' % database)
                    continue
                else:
                    if result['state'] != 'ERROR':
                        result['state'] = 'WARN'
                    result['messages']['warn'].append('Database %s: no collections found, empty database' % database)
                    continue

            # Validate collections
            if self.validate_collections:
                for collection in collections:
                    validation = db.validate_collection(collection)
                    if validation['valid']:
                        result['messages']['info'].append('Database %s: collection %s is valid' % (database, collection))
                        if result['state'] not in ['ERROR', 'WARN']:
                            result['state'] = 'OK'
                    else:
                        for e in validation['errors']:
                            result['messages']['error'].append('Database %s: %s' % (database, e))
                        result['state'] = 'ERROR'
            else:
                if result['state'] not in ['ERROR', 'WARN']:
                    result['state'] = 'OK'
                result['messages']['info'].append('Database %s: %d collections found' % (database, len(collections)))

        return result

    def check_connection(self):
        """
        Connect to Mongo, save connection in self.connection
        and return status and message
        """
        try:
            # Create connection and allow reading data from slave
            self.connection = pymongo.Connection(self.host, self.port, slave_okay=True, replicaSet=self.replicaset)
        except Exception as e:
            return {
                'state': 'ERROR',
                'messages' : {
                    'error' : [str(e)]
                }
            }

        return {
            'state': 'OK',
            'messages' : {
                'info': [self.connection.server_info()['sysInfo']]
            }
        }

    def check_members(self):
        """
        Check MongoDB peers and their status
        """
        if not self.connection:
            raise Exception('Not connected')

        db_admin = self.connection.admin

        try:
            status = db_admin.command('replSetGetStatus')
        except pymongo.errors.OperationFailure as e:
            # If Mongo isn't running clustered, return WARN, otherwise raise exception
            if str(e) == '''command SON([('replSetGetStatus', 1)]) failed: not running with --replSet''':
                return {
                    'state' : 'OK',
                    'messages' : {
                        'info' : ['Mongo is not running clustered']
                    }
                }
            else:
                raise

        # Check status of Mongo peers
        members = {
            'state' : None,
            'messages' : {
                'info' : [],
                'error': [],
                'warn' : [],
            }
        }

        for member in status['members']:
            if member.has_key('errmsg'):
                msg = 'Member %s is %s: %s' % (member['name'], member['stateStr'], member['errmsg'])
            else:
                msg = 'Member %s is %s' % (member['name'], member['stateStr'])

            # Check member state
            #
            #   0  WARN   Starting up, phase 1 (parsing configuration)
            #   1  OK     Primary
            #   2  OK     Secondary
            #   3  WARN   Recovering (initial syncing, post-rollback, stale members)
            #   4  ERROR  Fatal error
            #   5  WARN   Starting up, phase 2 (forking threads)
            #   6  ERROR  Unknown state (the set has never connected to the member)
            #   7  OK     Arbiter
            #   8  ERROR  Down
            #   9  WARN   Rollback
            #  10  ERROR  Removed
            if member['state'] in [1, 2, 7]:
                # Member is PRIMARY or SECONDARY
                members['messages']['info'].append(msg)

                if members['state'] not in ['ERROR', 'WARN']:
                    members['state'] = 'OK'
            elif member['state'] in [0, 3, 5, 9]:
                # Warning only
                members['messages']['warn'].append(msg)

                if members['state'] != 'ERROR':
                    members['state'] = 'WARN'
            else:
                # Error
                members['messages']['error'].append(msg)
                members['state'] = 'ERROR'

        return members
