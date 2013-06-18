#!/usr/bin/env python
"""
Not mine, found over there:
http://code.activestate.com/recipes/576819-logging-to-console-without-surprises/

Licensed under the MIT License and slightly modified.
"""
import logging
import sys

class LevelHandler(logging.StreamHandler):
    """A handler that logs to console in the sensible way.

    StreamHandler can log to *one of* sys.stdout or sys.stderr.

    It is more sensible to log to sys.stdout by default with only error
    (logging.ERROR and above) messages going to sys.stderr. This is how
    ConsoleHandler behaves.
    """
    def __init__(self, stream_greater_or_equal=sys.stderr,
                 stream_lower=sys.stdout,
                 level=logging.ERROR):
        """
        Initialize handler
        """
        # can't use line bellow, becuase StreamHandler is not
        # a new-style class
        #super(LevelHandler, self).__init__()
        logging.StreamHandler.__init__(self)
        self._level = level
        # keep it set as None
        self.stream = None
        self._stream_lower = stream_lower
        self._stream_greater_or_equal = stream_greater_or_equal

    def emit(self, record):
        """
        Overriden emit.
        """
        if record.levelno >= self._level:
            return self._emit(record, self._stream_greater_or_equal)
        else:
            return self._emit(record, self._stream_lower)

    def _emit(self, record, stream):
        self.stream = stream
        try:
            return logging.StreamHandler.emit(self, record)
            # can't use line bellow, because StreamHandler is not
            # a new-style class
            #return super(LevelHandler, self).emit(self, record)
        except:
            raise
        else:
            self.stream = None

    def flush(self):
        # Workaround a bug in logging module
        # See:
        #   http://bugs.python.org/issue6333
        if self.stream and hasattr(self.stream, 'flush') and not self.stream.closed:
            logging.StreamHandler.flush(self)
