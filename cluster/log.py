from os import getenv
from contextlib import contextmanager

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