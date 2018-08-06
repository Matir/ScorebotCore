#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Utilities & Functions

from random import randint
from django.conf.urls import url
from django.apps import AppConfig
from django.core.serializers import serialize
from django.core.handlers.wsgi import WSGIRequest
from scorebot import Authentication, Models, General, HTTP_HEADER
from django.core.exceptions import ValidationError, ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponse, HttpResponseNotFound, \
                        HttpResponseServerError
from scorebot.constants import AUTHENTICATE_MESSAGE_INVALID, AUTHENTICATE_MESSAGE_NO_HEADER, \
                               AUTHENTICATE_MESSAGE_INVALID_TOKEN, AUTHENTICATE_MESSAGE_EXPIRED, \
                               AUTHENTICATE_MESSAGE_MISSING_PERM
from django.db.models import AutoField, IntegerField, CharField, ManyToManyField, ManyToOneRel, OneToOneField, \
                             ForeignKey, ManyToManyRel

try:
    from ipware.ip import get_ip as _get_ip
except ImportError as err:
    Authentication.warning('Django IPware is not installed, all IP address lookups will be omitted!')

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


def lookup_address(hostname):
    return '127.0.0.1'


def hex_color():
    return ('#%s' % hex(randint(0, 0xFFFFFF))).replace('0x', '')


def new(name, save=False):
    model = get(name)
    if callable(model):
        instance = model()
        if instance is not None and save:
            instance.save()
        return instance
    return None


def authenticate(perms=None):
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
                Authentication.warning('[NOIP] Connected, but did not produce any valid HTTP headers!')
                return HttpResponseBadRequest(content=AUTHENTICATE_MESSAGE_INVALID)
            request.ip = ip(request)
            Authentication.debug('[%s] Connected to the Scorebot API!' % request.ip)
            if HTTP_HEADER not in request.META:
                Authentication.error('[%s] Connected without an Authorization Header!' % request.ip)
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_NO_HEADER)
            request.auth = Models('authorization').objects.get_key(request.META[HTTP_HEADER])
            if request.auth is None:
                Authentication.error('[%s] Submitted an invalid token!' % request.ip)
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_INVALID_TOKEN)
            if not request.auth:
                Authentication.error('[%s] Submitted an expired token "%s"!' % (request.ip, str(request.auth.token)))
                return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_EXPIRED)
            Authentication.debug('[%s] Connected to the Scorebot API, using token: "%s".' % (
                request.ip, str(request.auth.token.uid)
            ))
            if isinstance(perms, list):
                for item in perms:
                    if not request.auth[item]:
                        Authentication.error(
                            '[%s] Attempted to access function "%s" which requires the "%s" permission!'
                            % (request.ip, str(auth_func.__qualname__), item)
                        )
                        return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_MISSING_PERM.format(perm=str(item)))
            elif isinstance(perms, str) or isinstance(perms, int):
                if not request.auth[perms]:
                    Authentication.error(
                        '[%s] Attempted to access function "%s" which requires the "%s" permission!'
                        % (request.ip, str(auth_func.__qualname__), perms)
                    )
                    return HttpResponseForbidden(content=AUTHENTICATE_MESSAGE_MISSING_PERM.format(perm=str(perms)))
            Authentication.info(
                '[%s]: Successfully Authenticated using token "%s", passing control to function "%s".'
                % (request.ip, str(request.auth.token.uid), str(auth_func.__qualname__))
            )
            return auth_func(*args, **kwargs)
        return _auth_wrapped
    return _auth_wrapper


def authenticate_monitor():
    pass


def authenticate_team(field, required=None, perms=None, beacon=False, offensive=False):
    pass


def register_all_urls(urlpatterns, prefix='api'):
    if isinstance(prefix, str) and len(prefix) > 0:
        if prefix[0] == '/':
            prefix = prefix[1:]
        if prefix[len(prefix) - 1] == '/':
            prefix = prefix[:len(prefix) - 1]
    else:
        prefix = ''
    for model in Models.values():
        _register_model_url(dict(), model, None, None, prefix, urlpatterns)


def _register_model_function(request, *args, **kwargs):
    if 'model' not in kwargs:
        return HttpResponseNotFound()
    if request.method == 'GET':
        model = get(kwargs['model'])
        model_query = kwargs.get('%s_id' % kwargs['model'], None)
        if model_query is not None:
            try:
                model_result = model.objects.get(id=int(model_query))
            except ValueError as err:
                return HttpResponseBadRequest('{"result": "SBE4: %s"}' % str(err))
            except ObjectDoesNotExist:
                return HttpResponseNotFound('%s: %s' % (kwargs['model'].title(), model_query))
            except (MultipleObjectsReturned, Exception):
                return HttpResponseServerError('{"result": "SBE4: Multiple \'%s\' for \'%s\'!"}' % (
                    kwargs['model'].title(), model_query
                ))
            return HttpResponse(content=serialize('json', [model_result]))
        else:
            try:
                model_result = model.objects.filter(kwargs=request.GET.dict())
            except Exception:
                return HttpResponseServerError('{"result": "SBE4: Multiple \'%s\' for \'%s\'!"}' % (
                    kwargs['model'].title(), model_query
                ))
            return HttpResponse(content=serialize('json', model_result))
        """if
        try:

        except ValueError as err
            return HttpResponseBadRequest('{"result": "SBE4: %s"}' % str(err))


        try:
            obj = model.objects.get(id=int(kwargs['%s_id' % kwargs['model']]))
        except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned) as err:
            return HttpResponseBadRequest(str(err))
        if 'name' in kwargs:
            try:
                sub = getattr(obj, kwargs['name'])
            except AttributeError as err:
                return HttpResponseNotFound(str(err))
            if 'parent' in kwargs:
                return HttpResponse(serialize('json', sub.all()))
            return HttpResponse(str(sub))
        return HttpResponse(serialize('json', [obj]))"""
    return HttpResponse(str(args))


def _register_model_url(recurse, model, parent, name, path, urlpatterns):
    if name is None:
        name = model._meta.model_name.lower()
    if name in recurse:
        return
    else:
        recurse[name] = True
    path = '%s/%s' % (path, name)
    urlpatterns.append(url('^%s/$' % path, _register_model_function, kwargs={
        'model': model._meta.model_name.lower(), 'parent': None
    }))
    if parent is None:
        path = '%s/(?P<%s_id>[0-9]+)' % (path, name)
        urlpatterns.append(url('^%s/$' % path, _register_model_function, kwargs={
            'model': model._meta.model_name.lower(), 'parent': None
        }))
    else:
        urlpatterns.append(url('^%s/$' % path, _register_model_function, kwargs={
            'model': parent, 'parent': parent, 'name': name
        }))
    fields = None
    try:
        fields = getattr(model, '_meta').get_fields()
    except AttributeError:
        pass
    else:
        for field in fields:
            print(field.name)
            if isinstance(field, ForeignKey) or isinstance(field, ManyToManyField) or isinstance(field, OneToOneField):
                pass  #  _register_model_url(recurse, field.related_model, parent.copy(), field.name, path, urlpatterns)
            elif isinstance(field, ManyToOneRel):
                _register_model_url(recurse, field.related_model, name, field.name, path, urlpatterns)
            else:
                print(field.name, type(field))
                urlpatterns.append(url('^%s/%s/$' % (path, field.name), _register_model_function, kwargs={
                    'model': model._meta.model_name.lower(), 'name': field.name
                }))

# EOF
