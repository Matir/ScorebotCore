#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Core Scorebot v4 Class Instances
# Allows for static pointers to be implemented and added.

from os import makedirs
from sys import stderr, exit
from logging import Formatter
from os.path import join, isdir

# Core Version and Information
Name = 'Scorebotv4'
Version = 'v4.1-avacado'

# Core Logger Dictionary
Logs = dict()

# Core Models Dictionary
Models = dict()

# Core Logs
Auth = None
Jobs = None
Events = None
Default = None
Scoring = None

# Core Directories
TMP_DIRECTORY = '/var/run/scorebot'
LOG_DIRECTORY = join(TMP_DIRECTORY, Name.lower(), 'logs')
LOG_DIRECTORY_CACHE = join(TMP_DIRECTORY, Name.lower(), 'cache')

# Core Log Defaults and Constants
LOG_DEFAULT_PORT = None
LOG_DEFAULT_SERVER = None
LOG_DEFAULT_LEVEL = 'DEBUG'
LOG_DEFAULT_LOG = 'default'
LOG_FORMAT = Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# Core Constants
HTTP_GET = 'GET'
HTTP_POST = 'POST'
HTTP_AUTH_HEADER = 'HTTP_SBE_AUTH'

try:
    if not isdir(LOG_DIRECTORY):
        makedirs(LOG_DIRECTORY)
    if not isdir(LOG_DIRECTORY_CACHE):
        makedirs(LOG_DIRECTORY_CACHE)
except OSError as err:
    print('FATAL: Could not create Log and Cache Directories (%s, %s)! (%s)' %
          (LOG_DIRECTORY, LOG_DIRECTORY_CACHE, str(err)), file=stderr)
    exit(1)

try:
    # Core Log Import to prevent Loop Issues
    from scorebot.log import Log
    # Log Creation
    Auth = Log('auth', LOG_DEFAULT_LEVEL, LOG_DIRECTORY, LOG_DEFAULT_SERVER, LOG_DEFAULT_PORT)
    Jobs = Log('jobs', LOG_DEFAULT_LEVEL, LOG_DIRECTORY, LOG_DEFAULT_SERVER, LOG_DEFAULT_PORT)
    Events = Log('event', LOG_DEFAULT_LEVEL, LOG_DIRECTORY, LOG_DEFAULT_SERVER, LOG_DEFAULT_PORT)
    Scoring = Log('scoring', LOG_DEFAULT_LEVEL, LOG_DIRECTORY, LOG_DEFAULT_SERVER, LOG_DEFAULT_PORT)
    Default = Log(LOG_DEFAULT_LOG, LOG_DEFAULT_LEVEL, LOG_DIRECTORY, LOG_DEFAULT_SERVER, LOG_DEFAULT_PORT)
    Logs['auth'] = Auth
    Logs['jons'] = Jobs
    Logs[None] = Default
    Logs['events'] = Events
    Logs['scoring'] = Scoring
    Logs['default'] = Default
except OSError as err:
    print('FATAL: Could not setup core Log objects! (%s)' % str(err), file=stderr)
    exit(1)

Default.info('%s version: %s initilization complete!' % (Name, Version))

# EOF
