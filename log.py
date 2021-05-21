'''
A set of logging utilities for use by node_up.py
Of particular interest are the `indent` context manager, and the 
`traced` and `prompt` decorators.
'''

from os import getenv
from contextlib import contextmanager
from functools import wraps
from inspect import iscoroutinefunction as isasync

FATAL = 0
ERROR = 1
WARNING = 2
INFO = 3
DEBUG = 4
TRACE = 5
VERBOSE = 6
LOG_LEVEL = int(getenv('LOG_LEVEL', TRACE))
PREFIX = ''
INDENT_WIDTH = 0

@contextmanager
def indent(width, prefix=None):
  '''
  Increase the indent depth used by logging functions.
  Helps to make traces more readable.
  If `prefix` is provided, can also provide more information about the logging context
  '''
  global INDENT_WIDTH
  global PREFIX
  head = PREFIX
  components = []
  if head:
    components.append(head)
  if prefix:
    components.append(prefix)
  PREFIX = '|'.join(components)
  INDENT_WIDTH += width
  try:
    yield
  finally:
    INDENT_WIDTH -= width
    PREFIX = head

def should_log(level):
  return level > LOG_LEVEL

def log(level, *args, **kwargs):
  if level > LOG_LEVEL:
    return
  print(INDENT_WIDTH * '  ' + '[' + PREFIX + '] ', end='')
  print(*args, **kwargs)

def fatal(*args, **kwargs):
  log(FATAL, *args, **kwargs)


def error(*args, **kwargs):
  log(ERROR, *args, **kwargs)


def warning(*args, **kwargs):
  log(WARNING, *args, **kwargs)


def info(*args, **kwargs):
  log(INFO, *args, **kwargs)


def debug(*args, **kwargs):
  log(DEBUG, *args, **kwargs)

def trace(*args, **kwargs): log(TRACE, *args, **kwargs)

def verbose(*args, **kwargs):
  log(VERBOSE, *args, **kwargs)

def traced(s=None, prefix=None):
  '''
  A decorator used to automatically log function entry and increment the log level inside a function.
  Convenient for adding simple trace / progress logging.
  '''
  def decorator(f):
    if isasync(f):
      @wraps(f)
      async def decorated(*args, **kwargs):
        trace(s or f.__name__)
        with indent(2, prefix=prefix or f.__name__):
          return await f(*args, **kwargs)
      return decorated
    else:
      @wraps(f)
      def decorated(*args, **kwargs):
        trace(s or f.__name__)
        with indent(2, prefix=prefix or f.__name__):
          return f(*args, **kwargs)
      return decorated
  return decorator


def prompt(s):
  '''
  A decorator used to request permission to run a function from the user
  '''
  def decorator(f):
    if isasync(f):
      @wraps(f)
      async def decorated(*args, **kwargs):
        if input(INDENT_WIDTH * ' ' + s + '? (y/n): ') != 'y':
          return
        return await f(*args, **kwargs)
      return decorated
    else:
      @wraps(f)
      def decorated(*args, **kwargs):
        if input(INDENT_WIDTH * ' ' + s + '? (y/n): ') != 'y':
          return
        return f(*args, **kwargs)
      return decorated
  return decorator