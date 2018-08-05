#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Utilities & Functions

from random import randint
from django.apps import AppConfig
from django.core.handlers.wsgi import WSGIRequest
from django.core.exceptions import ValidationError
from scorebot import Auth, HTTP_AUTH_HEADER, Models, Default
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from scorebot.constants import AUTHENTICATE_MESSAGE_INVALID, AUTHENTICATE_MESSAGE_NO_HEADER, \
                               AUTHENTICATE_MESSAGE_INVALID_TOKEN, AUTHENTICATE_MESSAGE_EXPIRED, \
                               AUTHENTICATE_MESSAGE_MISSING_PERM

try:
    from ipware.ip import get_ip as _get_ip
except ImportError as err:
    Auth.warning('Django IPware is not installed, all IP address lookups will be omitted!')

    def _get_ip(request):
        return 'ERR-DJANGO-IPWARE-MISSING'


class API(AppConfig):
    name = 'scorebot_api'
    verbose_name = 'Scorebot4 API'


class Database(AppConfig):
    name = 'scorebot_db'
    verbose_name = 'Scorebot4 Database'


class ScorebotError(ValidationError):
    def __init__(self, error):
        ValidationError.__init__(self, error)


def get(name):
    return Models.get(name.lower(), None)


def ip(request):
    return str(_get_ip(request))


def hex_color():
    return ('#%s' % hex(randint(0, 0xFFFFFF))).replace('0x', '')


def new(name, save=True):
    model = get(name)
    if callable(model):
        instance = model()
        if instance is not None and save:
            instance.save()
        return instance
    return None


def authenticate(requires=None):
    def _auth_wrapper(auth_func):
        def _auth_wrapped(*args, **kwargs):
            request = None
            for argument in args:
                if isinstance(argument, WSGIRequest):
                    request = argument
                    break
            if request is None:
                for value in kwargs.values():
                    if isinstance(value, WSGIRequest):
                        request = value
                        break
            if not isinstance(request, WSGIRequest):
                Auth.warning('[NOIP] Connected, but did not produce any valid HTTP headers!')
                return HttpResponseBadRequest(content=AUTHENTICATE_MESSAGE_INVALID)
            client = ip(request)
            Auth.debug('[%s] Connected to the Scorebot API!' % client)
            Default.debug('[%s] Connected to the Scorebot API!' % client)
            if HTTP_AUTH_HEADER not in request.META:
                Auth.error('[%s] Connected without an Authorization Header!' % client)
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_NO_HEADER)
            request.auth = get('Authorization').objects.get_key(request.META[HTTP_AUTH_HEADER])
            if request.auth is None:
                Auth.error('[%s] Submitted an invalid token!' % client)
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_INVALID_TOKEN)
            if not request.auth:
                Auth.error('[%s] Submitted an expired token "%s"!' % (client, str(request.auth.token)))
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_EXPIRED)
            Auth.debug('[%s] Connected to the Scorebot API, using token: "%s".' % (client, str(request.auth.token.uid)))
            if isinstance(requires, list):
                for item in requires:
                    if not request.auth[item]:
                        Auth.error('[%s] Attempted to access function "%s" which requires the "%s" permission!' % (
                            client, str(auth_func.__qualname__), item
                        ))
                        return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_MISSING_PERM.format(perm=str(item)))
            elif isinstance(requires, str) or isinstance(requires, int):
                if not request.auth[requires]:
                    Auth.error('[%s] Attempted to access function "%s" which requires the "%s" permission!' % (
                        client, str(auth_func.__qualname__), requires
                    ))
                    return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_MISSING_PERM.format(perm=str(requires)))
            Auth.info('[%s]: Successfully Authenticated using token "%s", passing control to function "%s".' % (
                client, str(request.auth.token.uid), str(auth_func.__qualname__)
            ))
            del client
            return auth_func(*args, **kwargs)
        return _auth_wrapped
    return _auth_wrapper

# EOF
