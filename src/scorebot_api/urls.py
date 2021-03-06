#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Djano URLS File

from django.urls import path
from django.conf.urls import url
from django.contrib.admin import site
from scorebot.util import register_all_urls
from scorebot_api.views import job, flag, beacon, ports, register, mapper, \
        scoreboard, purchase, token_check, new_resource

urlpatterns = [
    path('admin/', site.urls),
    url(r'^api/job$', job, name='job'),
    url(r'^api/job/$', job, name='job'),
    url(r'^api/flag/$', flag, name='flag'),
    url(r'^api/beacon/$', beacon, name='beacon'),
    url(r'^api/beacon/port/$', ports, name='ports'),
    url(r'^api/register/$', register, name='register'),
    url(r'^api/purchase/<?P<team_id>[0-9]+)$', purchase, name='purchase'),
    url(r'^api/token$', token_check, name='token_check'),
    url(r'^api/new_resource$', new_resource, name='new_resource'),
    url(r'^api/mapper/(?P<gid>[0-9]+)$', mapper, name='mapper'),
    url(r'^api/mapper/(?P<gid>[0-9]+)/$', mapper, name='mapper'),
    url(r'^api/scoreboard/(?P<gid>[0-9]+)/$', scoreboard, name='scoreboard'),
]

#register_all_urls(urlpatterns, '/api/models/')


# EOF
