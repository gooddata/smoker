#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2013, GoodData(R) Corporation. All rights reserved

"""
ProgressBar util

Using by with syntax is preferred, otherwise you have to call progress.stop() for cleanup.

Typical usage (with pool of threads):

    with ProgressBar(len(pool)) as progress:
        while progress.get_left():
            done = 0
            for t in pool:
                if not t.isAlive():
                    done += 1
            progress.set_done(done)


Or when you are having pool of threads, you can use following shorter syntax:

    with ProgressBar(len(pool)) as progress:
        progress.wait_pool(pool)

And it's always good idea to fallback to non-progress wait (catch NonInteractiveError exception)

from util.progressbar import ProgressBar, NonInteractiveError
try:
    progress = ProgressBar(len(pool))
except NonInteractiveError as e:
    print e
    # fallback to non-progress wait
"""

import sys
import numbers
import threading
import time

from smoker.util import console

### Exceptions
class InvalidAnimationError(Exception):
    pass

class NonInteractiveError(Exception):
    pass

### Main class
class ProgressBar(threading.Thread, object):
    """
    Progressbar instance
    """
    elements = None
    template = None
    speed    = 0.08

    items_count = None
    items_done  = None

    def __init__(self, items, speed=None, template=None, elements=None, no_check_interactive=False):
        """
        Initialize progressbar
        Set parameters, initialize threading.Thread
        """
        assert isinstance(items, numbers.Integral), "Parameter items must be integral number"
        assert (isinstance(speed, numbers.Real) or speed is None), "Parameter speed must be real number"

        if not no_check_interactive:
            if not console.is_interactive_shell():
                raise NonInteractiveError("Shell seems to be non-interactive. Can't use progress bar.")

        self.items_count = items
        self.items_done  = 0

        self.speed = speed or self.speed

        if not elements:
            # Initialize basic elements
            self.elements = {
                'wheel' : WheelElement(self),
                'bar'   : ProgressElement(self),
                'counter' : CounterElement(self),
            }

        if not template:
            # Set basic template
            self.template = '{wheel} {bar}\t{counter}'

        # Run Thread constructor, we want to be daemonic thread
        super(ProgressBar, self).__init__()
        self.daemon = True

    def add_done(self, count=1):
        """
        Add count of items as done
        """
        assert isinstance(count, numbers.Integral), "Count must be integral number"
        self.items_done += count

    def get_left(self):
        """
        Return number of left items
        """
        return self.items_count - self.items_done

    def set_done(self, done=None):
        """
        Set all items as done or specific count
        """
        if done is not None:
            assert isinstance(done, numbers.Integral), "Done count must be integral number"
            self.items_done = done
        else:
            self.items_done = self.items_count

    def run(self):
        """
        Run thread
        While we have undone items, print progressbar
        """
        while self.items_done < self.items_count:
            # Cleanup to fix progress after terminal resize
            try:
                width, height = console.get_terminal_size()
            except IOError:
                # Fallback to default values
                width, height = (80, 37)
            sys.stdout.write('\r%s' % (width * ' '))

            # Write progress
            sys.stdout.write('\r %s' % self.get_progress())
            sys.stdout.flush()
            time.sleep(self.speed)

    def stop(self):
        """
        This function has to be called after progress bar stop to do the cleanup
        """
        print

    def __exit__(self, type, value, traceback):
        """
        This function is called when using with syntax
        """
        self.stop()

    def __enter__(self):
        """
        This function is called when using with syntax
        Returns self
        """
        self.start()
        return self

    def get_progress(self):
        """
        Format and return progress bar
        """
        progress = self.template.format(**self.elements)
        return progress

    def wait_pool(self, pool):
        """
        Accept list pool of threads, watch if they are alive and update progress
        """
        assert isinstance(pool, list), "Parameter pool must be list of Thread objects"

        while self.get_left():
            done = 0
            for t in pool:
                assert isinstance(t, threading.Thread),\
                    "Object in pool must be instance of threading.Thread not %s" % type(t)
                if not t.isAlive():
                    done += 1
            self.set_done(done)
            time.sleep(1)

### Elements
class Element(object):
    """
    Base Element class
    """
    def __init__(self, main):
        """
        Initialize Element
        Store main class instance
        """
        self.main = main

class AnimationElement(Element):
    """
    Base animation element class
    """
    animation = None
    index = None

    def __str__(self):
        """
        Return current state
        """
        # Update state if we are animated element
        if isinstance(self.animation, list):
            index = self.__update_index()
            return str(self.animation[index])
        else:
            raise InvalidAnimationError('Animation has to be list not %s' % type(self.animation))

    def __update_index(self):
        """
        Update animation state
        Return index
        """
        if self.index is None:
            self.index = 0
        else:
            # Code bellow is faster than catching IndexError exception
            self.index += 1
            if len(self.animation) == self.index:
                self.index = 0
        return self.index

class WheelElement(AnimationElement):
    """
    Element that renders spinning wheel
    """
    animation = ['|', '/', '–', '\\']

class ProgressElement(Element):
    """
    Basic progress element
    """
    progress_part  = '='
    progress_start = ''
    progress_end   = '>'
    bar_start = '['
    bar_end   = ']'
    bar_width  = 80

    def __str__(self):
        """
        Render progress bar
        """
        return self.get_bar()

    def get_bar(self):
        """
        calculate and return progress bar string
        """
        # Get terminal size
        try:
            width, height = console.get_terminal_size()
        except IOError:
            # Fallback to default values
            width, height = (80, 37)

        # Bar should be half a terminal width
        self.bar_width = width / 2

        # Calculate step size
        part_size = float(self.bar_width) / float(self.main.items_count)
        bar_size  = int(part_size * self.main.items_done)

        info = {
            'bar_start' : self.bar_start,
            'progress_start' : self.progress_start,
            'bar' : '%s%s' % (bar_size * self.progress_part, self.progress_end),
            'bar_width': self.bar_width,
            'bar_end' : self.bar_end
        }
        render = '{bar_start}{progress_start}{bar:<{bar_width}}{bar_end}'.format(**info)

        return render

class CounterElement(Element):
    """
    Basic counter element
    """
    template = '{done}/{total}'

    def __str__(self):
        counter = self.template.format(**{'done' : self.main.items_done, 'total' : self.main.items_count })
        return counter
