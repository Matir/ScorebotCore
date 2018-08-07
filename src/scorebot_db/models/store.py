#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Team Django Models

# from sys import maxsize
# from django.contrib.auth.models import User
# from scorebot.util import ScorebotError, hex_color
from django.db.models import Model, IntegerField, CharField
# SET_NULL, ForeignKey, ManyToManyField, CASCADE, OneToOneField, BooleanField, \
#                             CharField, ImageField, BigIntegerField, PositiveIntegerField, \
#                             PositiveSmallIntegerField


class Item(Model):
    class Meta:
        verbose_name = '[Store] Item'
        verbose_name_plural = '[Store] Items'

    sid = IntegerField(null=False)
    name = CharField(max_length=128, null=False)


class Store(Model):
    class Meta:
        verbose_name = '[Store] Storefront'
        verbose_name_plural = '[Store] Storefronts'

# EOF
