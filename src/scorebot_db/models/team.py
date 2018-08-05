#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Team Django Models

from uuid import UUID
from sys import maxsize
from html import escape
from scorebot import Default
from datetime import timedelta
from django.utils.timezone import now
from json import loads, JSONDecodeError
from django.http import HttpResponseBadRequest
from scorebot.util import new, get, hex_color, ip
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from scorebot.constants import MESSAGE_INVALID_FORMAT, MESSAGE_INVALID_ENCODING, TEAM_DEFAULT_FIELD, \
                               TEAM_MESSAGE_MISSING_FIELD, TEAM_MESSAGE_NO_TEAM, TEAM_MESSAGE_EXPIRED, \
                               TEAM_MESSAGE_NOT_OFFENSIVE, MESSAGE_GAME_NO_RUNNING, TEAM_DEFAULT_TOKEN_DAYS
from django.db.models import Model, SET_NULL, ForeignKey, OneToOneField, BooleanField, CharField, ImageField, CASCADE, \
                             PositiveSmallIntegerField, BigIntegerField, PositiveIntegerField, ManyToManyField, Manager


class TeamManager(Manager):
    def get_team(self, uuid, beacon=False):
        try:
            uuid_string = UUID(str(uuid))
        except ValueError as err:
            return None
        else:
            try:
                token = get('Token').objects.get(uid=uuid_string)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                return None
            else:
                try:
                    if beacon:
                        return self.get(registered__in=[token])
                    return self.get(token=token)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    return None
                finally:
                    del token
            finally:
                del uuid_string
        return None

    def get_team_token(self, uuid, beacon=False):
        try:
            uuid_string = UUID(str(uuid))
        except ValueError as err:
            return None, None
        else:
            try:
                token = get('Token').objects.get(uid=uuid_string)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                return None, None
            else:
                try:
                    if beacon:
                        return self.get(registered__in=[token]), token
                    return self.get(token=token), token
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    return None, None
            finally:
                del uuid_string
        return None, None

    def get_team_json(self, request, field=TEAM_DEFAULT_FIELD, beacon=False, offensive=False):
        client = ip(request)
        try:
            json_str = request.body.decode('UTF-8')
        except UnicodeDecodeError:
            Default.error('[%s] Client attempted to submit an improperly encoded request!' & client)
            return None, None, None, HttpResponseBadRequest(content=MESSAGE_INVALID_ENCODING)
        try:
            json_data = loads(json_str)
        except JSONDecodeError:
            Default.error('[%s] Client attempted to submit an improperly JSON formatted request!' & client)
            return None, None, None, HttpResponseBadRequest(content=MESSAGE_INVALID_FORMAT)
        finally:
            del json_str
        if field not in json_data:
            Default.error('[%s] Data submitted by client is missing requested field "%s"!' & (client, field))
            return None, None, None, HttpResponseBadRequest(content=TEAM_MESSAGE_MISSING_FIELD.format(field=field))
        Default.debug('[%s] Client connected with token "%s" to request a Team.' % (
            client, str(request.auth.token.uid)
        ))
        team, token = self.get_team_token(uuid=json_data[field], beacon=beacon)
        if team is None:
            Default.info('[%s] Client attempted to use value "%s" to request a non-existant Team!' % (
                client, json_data[field])
            )
            return None, None, None, HttpResponseBadRequest(content=TEAM_MESSAGE_NO_TEAM)
        Default.debug('[%s] Client connected and requested Team "%s" with Token "%s".' % (
            client, team.get_path(), json_data[field]
        ))
        if not team.token.__bool__():
            Default.error('[%s] Client attempted to use token "%s" that has expired!' % (client, str(team.token.uid)))
            return None, None, None, HttpResponseBadRequest(content=TEAM_MESSAGE_EXPIRED)
        if offensive:
            team = team.get_playingteam()
            if team is None or not team.offensive:
                Default.error(
                    '[%s] Client connected and requested Team "%s" with Token "%s", but Team is not marked Offensive!'
                    % (client, team.get_path(), json_data[field])
                )
                return None, None, None, HttpResponseBadRequest(content=TEAM_MESSAGE_NOT_OFFENSIVE)
        if not team.get_game().__bool__():
            Default.error('[%s] Client connected and requested Team "%s" that is not currently in a running Game!' % (
                client, team.get_path()
            ))
            return HttpResponseBadRequest(content=MESSAGE_GAME_NO_RUNNING)
        return team, json_data, token, None


class Team(Model):
    class Meta:
        verbose_name = '[Team] BaseTeam'
        verbose_name_plural = '[Team] BaseTeams'

    class Options:
        json = False
        access = False

    game = ForeignKey('scorebot_db.Game', related_name='teams', on_delete=CASCADE)

    def update(self):
        self.__subclass__().__update__()

    def __str__(self):
        return self.__subclass__().__string__()

    def __len__(self):
        return abs(self.get_score())

    def get_json(self):
        return self.__subclass__().__json__()

    def get_path(self):
        return '%s\\%s' % (self.game.get_path(), self.get_descriptor())

    def get_game(self):
        return self.game

    def get_name(self):
        return self.__subclass__().__objname__()

    def __json__(self):
        return None

    def get_score(self):
        return self.__subclass__().__score__()

    def __score__(self):
        return 0

    def __update__(self):
        pass

    def __string__(self):
        return '[BaseTeam] %s' % self.get_path()

    def __objname__(self):
        return 'Invalid'

    def __subclass__(self):
        try:
            return self.playingteam
        except AttributeError:
            pass
        try:
            return self.scoringteam.playingteam
        except AttributeError:
            pass
        try:
            return self.systemteam.scoringteam.playingteam
        except AttributeError:
            pass
        try:
            return self.scoringteam
        except AttributeError:
            pass
        try:
            return self.systemteam.scoringteam
        except AttributeError:
            pass
        try:
            return self.systemteam
        except AttributeError:
            pass
        return self

    def __lt__(self, other):
        return isinstance(other, Team) and other.get_score() > self.get_score()

    def __gt__(self, other):
        return isinstance(other, Team) and other.get_score() < self.get_score()

    def __eq__(self, other):
        return isinstance(other, Team) and other.get_score() == self.get_score()

    def get_descriptor(self):
        return '%d-%s' % (self.id, self.get_name())

    def get_playingteam(self):
        try:
            return self.playingteam
        except AttributeError:
            pass
        try:
            return self.scoringteam.playingteam
        except AttributeError:
            pass
        try:
            return self.systemteam.scoringteam.playingteam
        except AttributeError:
            pass
        return None

    def __transaction__(self, transaction):
        pass

    def add_transaction(self, transaction):
        return self.__subclass__().__transaction__(transaction)


class SystemTeam(Team):
    class Meta:
        verbose_name = '[Team] SystemTeam'
        verbose_name_plural = '[Team] SystemTeams'

    name = CharField('Team Name', max_length=64)

    def __score__(self):
        return maxsize

    def __string__(self):
        return '[SystemTeam] %s' % self.get_path()

    def __objname__(self):
        return self.name


class ScoringTeam(SystemTeam):
    class Meta:
        verbose_name = '[Team] ScoringTeam'
        verbose_name_plural = '[Team] ScoringTeams'

    objects = TeamManager()
    score = BigIntegerField('Team Score', default=0, editable=False)
    token = OneToOneField('scorebot_db.Token', on_delete=SET_NULL, null=True, blank=True)
    stack = OneToOneField('scorebot_db.Transaction', on_delete=SET_NULL, null=True, blank=True)

    def __score__(self):
        return self.score

    def __update__(self):
        self.score = self.stack.update()
        self.save()

    def __string__(self):
        return '[ScoringTeam] %s: %d' % (self.get_path(), self.get_score())

    def save(self, *args, **kwargs):
        if self.token is None:
            self.token = new('Token', True)
        SystemTeam.save(self, *args, **kwargs)
        if self.stack is None:
            stack = new('Transaction', False)
            stack.source = self
            stack.destination = self
            stack.save()
            self.stack = stack
            SystemTeam.save(self, *args, **kwargs)

    def transfer(self, team, value):
        transfer = new('Transfer', False)
        transfer.source = self
        transfer.value = value
        transfer.destination = team
        transfer.save()
        self.add_transaction(transfer)
        return transfer

    def __transaction__(self, transaction):
        transaction.previous = self.stack
        transaction.save()
        self.stack = transaction
        self.score += self.stack.get_score()
        self.save()
        Default.info('Transaction "%s" with value "%d" was added to "%s" from "%s"!' % (
            transaction.get_name(), transaction.get_score(), self.get_path(), transaction.source.get_path()
        ))
        transaction.log()


class PlayingTeam(ScoringTeam):
    class Meta:
        verbose_name = '[Team] Player Team'
        verbose_name_plural = '[Team] Player Teams'

    objects = TeamManager()
    logo = ImageField('Team Logo', null=True, blank=True)
    offensive = BooleanField('Team Can Attack', default=False)
    minimal = BooleanField('Team Score Is Hidden', default=False)
    color = CharField('Team Color', max_length=9, default=hex_color)
    store = PositiveIntegerField('Team Store ID', blank=True, null=True)
    deduction = PositiveSmallIntegerField('Team Score Deduction Percentage', default=0)
    registered = ManyToManyField('scorebot_db.Token', blank=True, related_name='beacon_tokens')
    assets = ForeignKey('scorebot_db.Range', on_delete=SET_NULL, null=True, blank=True, related_name='team')
    membership = ForeignKey('scorebot_db.Membership', blank=True, null=True, on_delete=SET_NULL, related_name='teams')

    def __json__(self):
        return {
            'color': self.color,
            'name': self.get_name(),
            'mininal': self.minimal,
            'score': self.get_score(),
            'offensive': self.offensive,
            'logo': self.logo.url if bool(self.logo) else None,
            'assets': self.assets.get_json() if self.assets is not None else None
        }

    def __string__(self):
        return '[PlayingTeam] %s: %d' % (self.get_path(), self.get_score())

    def get_scoreboard(self, old=False):
        if old:
            return {
                'id': self.id,
                'name': escape(self.get_name()),
                'color': self.color,
                'offense': self.offensive,
            }
        team_json = {'id': self.id, 'name': html.escape(self.name),
                     'color': '#%s' % str(hex(self.color)).replace('0x', '').zfill(6),
                     'score': {'total': self.score.get_score(), 'health': self.score.uptime},
                     'offense': self.offensive,
                     'flags': {'open': self.flags.filter(enabled=True, captured__isnull=True).count(),
                               'lost': self.flags.filter(enabled=True, captured__isnull=False).count(),
                               'captured': self.attacker_flags.filter(enabled=True).count()},
                     'tickets': {'open': self.tickets.filter(closed=False).count(),
                                 'closed': self.tickets.filter(closed=True).count()},
                     'hosts': [h.get_json_scoreboard() for h in self.hosts.all()],
                     'logo': (self.logo.url if self.logo.__bool__() else 'default.png'),
                     'beacons': self.get_beacons(), 'minimal': self.minimal}
        return team_json

    def add_beacon_token(self, days=TEAM_DEFAULT_TOKEN_DAYS):
        token = new('Token', False)
        if days > 0:
            token.expires = (now() - timedelta(days=days))
        token.save()
        self.registered.add(token)
        self.save()
        Default.info('Team "%s" has registered a Beacon Token "%s".' % (self.get_path(), str(token.uid)))
        return token

# EOF
