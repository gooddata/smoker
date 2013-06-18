#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

"""
Module tap provides interface for generating TAP (Test Anything Protocol) outputs

http://en.wikipedia.org/wiki/Test_Anything_Protocol


Usage example:

from util.tap import TapTest, Tap

# Host
tap_host1 = TapTest('host1', ok=True)

# Host's tests
tap_host1_tests = {
    'test1' : TapTest('test1', ok=True),
    'test2' : TapTest('test1', ok=True)
}
tap_host1.add_subtests(tap_host1_tests.values())

# Subtests for test2
tap_host_test2_subtest1 = TapTest('subtest1', ok=True)
tap_host1_tests['test2'].add_subtest(tap_host_test2_subtest1)

# Initialize Tap instance and add it into group
tap = Tap()
tap.add_test(tap_host1)

# Dump result
print tap.dump()

# Output will be:
# 1..1
# ok 1 - host1
#   1..2
#   ok 1 - test1
#   ok 2 - test1
#       1..1
#       ok 1 - subtest1
"""

import re

class Tap(object):
    """
    Class to group TapTest objects
    """
    tests = None
    index = None

    def __init__(self):
        """
        Initialize Tap instance
        """
        self.index = 1
        self.tests = []

    def add_test(self, test):
        """
        Add TapTest instance
        Return test index
        """
        assert isinstance(test, TapTest), 'test parameter must be instance of TapTest'

        test.index = self.index
        self.tests.append(test)
        self.index += 1

        return test.index

    def add_tests(self, tests):
        """
        Add list of TapTest instances
        """
        assert isinstance(tests, list), 'tests parameter must be list'

        for test in tests:
            assert isinstance(test, TapTest), 'test %s is not instance of TapTest' % test
            self.add_test(test)

    def dump(self):
        """
        Dump all tests into tap structure
        """
        dump = []

        dump.append('1..%s' % len(self.tests))
        for test in self.tests:
            dump.append(test.dump())

        return '\n'.join(dump)

class TapTest(object):
    """
    Single TAP test result
    """
    name = None
    status = None
    messages = None
    index = None

    subtests = None
    subtests_index = None

    def __init__(self, name, ok=True, messages=None):
        """
        Initialize instance
        """
        self.name = name
        self.index = 1
        self.subtests_index = 1
        self.subtests = []

        if ok is True:
            self.status = 'ok'
        else:
            self.status = 'not ok'
        self.messages = messages

    def add_subtest(self, test):
        """
        Add TapTest instance as subtest
        Return subtest index
        """
        test.index = self.subtests_index
        self.subtests.append(test)
        self.subtests_index += 1

        return test.index

    def add_subtests(self, tests):
        """
        Add list of TapTest instances
        """
        assert isinstance(tests, list), 'tests parameter must be list'

        for test in tests:
            assert isinstance(test, TapTest), 'test %s is not instance of TapTest' % test
            self.add_subtest(test)

    def dump(self):
        """
        Dump TapTest result into TAP
        Should be used from Tap instance to dump all results

        Dump messages in YAMLish format
        """
        dump = []
        dump.append('%s %s - %s' % (self.status, self.index, self.name))
        if self.messages:
            messages = []
            for key, values in self.messages.iteritems():
                if values:
                    messages.append('\t- %s:' % key)
                    for msg in values:
                        messages.append("\t\t- %s" % msg)
            if messages:
                messages.insert(0, '---')
                messages.append('...')
                dump.append('\n'.join(messages))
        if self.subtests:
            dump_subtests = []
            dump_subtests.append('\t1..%s' % len(self.subtests))
            for test in self.subtests:
                dump_subtests.append(test.dump())
            dump.append(re.sub('\n', '\n\t', '\n'.join(dump_subtests)))

        return '\n'.join(dump)
