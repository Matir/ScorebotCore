#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Scorebot Team Django Models

from random import choice
from scorebot import Default, Events
from django.utils.timezone import now
from scorebot.util import new, ScorebotError, get
from ipaddress import IPv4Network, IPv4Address
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden, HttpResponse
from scorebot.constants import SERVICE_PROTOCOLS, SERVICE_STATUS, HOST_VALUE_DEFAULT, FLAG_VALUE_DEFAULT, \
                               SERVICE_VALUE_DEFAULT, CONTENT_VALUE_DEFAULT, HOST_MESSAGE_INVALID_IP, \
                               HOST_MESSAGE_NO_HOST, MESSAGE_GAME_NO_RUNNING, HOST_MESSAGE_BEACON_EXISTS, \
                               GAME_RUNNING
from django.db.models import Model, SET_NULL, ForeignKey, ManyToManyField, CASCADE, OneToOneField, BooleanField, \
                             CharField, TextField, PositiveSmallIntegerField, GenericIPAddressField, SlugField, \
                             DateTimeField, Manager


class FlagManager(Manager):
    def get_next_flag(self, team):
        game = team.get_game()
        if game.__bool__():
            try:
                flags = self.exclude(host__range__team=team).filter(
                    host__range__team__game=game, enabled=True, host__enabled=True, stolen__isnull=True
                )
                if len(flags) > 0:
                    return choice(flags)
                return None
            except IndexError:
                return None
            finally:
                del game
        return None

    def get_flag_query(self, team, flag):
        game = team.get_game()
        if game.__bool__():
            try:
                flag = self.exclude(host__range__team=team).get(
                    host__range__team__game=game, flag__exact=flag, enabled=True, host__enabled=True
                )
            except ObjectDoesNotExist:
                return None
            except MultipleObjectsReturned:
                Default.warning(
                    '%s attempted to get Flag "%s", but returned multiple Flags, multiple Flags have the vaue "%s"!'
                    % (team.get_path(), flag, flag)
                )
            else:
                return flag
            finally:
                del game
        return None


class HostManager(Manager):
    def get_beacon(self, team, token, address):
        try:
            target = IPv4Address(address)
        except ValueError:
            Default.error('Team "%s" reported a Beacon for an invalid IP address "%s"!' % (team.get_path(), address))
            return HttpResponseBadRequest(content=HOST_MESSAGE_INVALID_IP)
        Default.info('Received a Beacon request by Team "%s" for address "%s"!' % (team.get_path(), address))
        host = None
        ghost = False
        try:
            host = self.exclude(range__team=team).get(ip=address)
        except MultipleObjectsReturned:
            Default.error('Team "%s" reported a Beacon for an invalid IP address "%s" that matches multiple Hosts!' % (
                team.get_path(), address
            ))
            return HttpResponseBadRequest(content=HOST_MESSAGE_INVALID_IP)
        except ObjectDoesNotExist:
            ghost = True
            try:
                host = get('BeaconHost').objects.exclude(range__team=team).get(ip=address)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                pass
            if host is None:
                Default.info(
                    'Beacon request by Team "%s" for address "%s" does not match a known host, will attempt to match!'
                    % (team.get_path(), address)
                )
                victim = None
                for match in team.get_game().teams.exclude(id=team.id):
                    match_playing = match.get_playingteam()
                    if match_playing is None or match_playing.assets is None:
                        continue
                    try:
                        network = IPv4Network(match_playing.assets.subnet)
                    except ValueError:
                        Default.warning('Team "%s" does not have a valid subnet entered for it\'s range "%s"!' % (
                            match.get_path(), match_playing.assets.subnet
                        ))
                        continue
                    else:
                        if target in network:
                            victim = match_playing
                            break
                    finally:
                        del match_playing
                if victim is None:
                    Default.error(
                        'Beacon request by Team "%s" for address "%s" does not match a known host or Team subnet range!'
                        % (team.get_path(), address)
                    )
                    return HttpResponseNotFound(content=HOST_MESSAGE_NO_HOST)
                Default.debug(
                    'Creating BeaconHost due to Beacon request by Team "%s" for address "%s" that matches Team "%s" '
                    'range!' % (team.get_path(), address, victim.get_path())
                )
                host = new('BeaconHost', False)
                host.ip = address
                host.range = victim.assets
                host.save()
                del victim
        del target
        Default.debug('Received Beacon request by Team "%s" for Host "%s"!' % (team.get_path(), host.get_path()))
        if not host.get_game().__bool__():
            Default.error('Received Beacon request by Team "%s" for Host "%s" for a non-running Game!' % (
                team.get_path(), host.get_path()
            ))
            return HttpResponseBadRequest(content=MESSAGE_GAME_NO_RUNNING)
        if host.get_game().id != team.get_game().id:
            Default.error('Received Beacon request by Team "%s" for Host "%s" not in the same Game!' % (
                team.get_path(), host.get_path()
            ))
            return HttpResponseBadRequest(content=HOST_MESSAGE_NO_HOST)
        try:
            beacon = host.beacons.get(end__isnull=True, owner=team)
        except MultipleObjectsReturned:
            Default.warning('Received Beacon request by Team "%s" for Host "%s" attempting to add multiple Beacons!' % (
                team.get_path(), host.get_path()
            ))
            return HttpResponseForbidden(content=HOST_MESSAGE_BEACON_EXISTS)
        except ObjectDoesNotExist:
            Events.info('Created a new Beacon on Host "%s" owned by Team "%s" from "%s"!' % (
                host.get_path(), host.get_team().get_path(), team.get_path()
            ))
            Default.info('Created a new Beacon on Host "%s" owned by Team "%s" from "%s"!' % (
                host.get_path(), host.get_team().get_path(), team.get_path()
            ))
            team.get_game().event('%s has compromised a Host on %s\'s network!' % (
                team.get_name(), host.get_team().get_name()
            ))
            beacon = new('Beacon', False)
            beacon.owner = team
            if ghost:
                beacon.ghost = host
            else:
                beacon.host = host
        beacon.update = now()
        beacon.token = token
        beacon.save()
        return HttpResponse(status=201)


class DNS(Model):
    class Meta:
        verbose_name = '[Range] DNS Server'
        verbose_name_plural = '[Range] DNS Servers'

    ip = GenericIPAddressField('DNS Server Address', protocol='both', unpack_ipv4=True)

    def __str__(self):
        return '[DNS] %s' % str(self.ip)


class Flag(Model):
    class Meta:
        verbose_name = '[Range] Flag'
        verbose_name_plural = '[Range] Flags'

    objects = FlagManager()
    name = SlugField('Flag Name', max_length=64)
    flag = CharField('Flag Value', max_length=128)
    enabled = BooleanField('Flag Enabled', default=True)
    description = TextField('Flag Description', null=True, blank=True)
    host = ForeignKey('scorebot_db.Host', on_delete=CASCADE, related_name='flags')
    value = PositiveSmallIntegerField('Flag Score Value', default=FLAG_VALUE_DEFAULT)
    stolen = ForeignKey('scorebot_db.PlayingTeam', on_delete=SET_NULL, null=True, blank=True, related_name='captured')

    def clear(self):
        Default.info('Clearing Flag "%s".' % self.get_path())
        self.stolen = None
        self.save()

    def __str__(self):
        if self.stolen is not None:
            return '[Flag] %s\\%s %d (Stolen: %s)' % (
                self.host.get_path(), self.name, self.value, self.stolen.get_path()
            )
        return '[Flag] %s\\%s %d' % (self.host.get_path(), self.name, self.value)

    def __bool__(self):
        return self.enabled and self.stolen is None

    def get_path(self):
        return '%s\\%s' % (self.host.get_path(), self.name)

    def get_name(self):
        return self.name

    def get_game(self):
        return self.host.get_game()

    def get_team(self):
        return self.host.get_team()

    def get_json(self):
        return {
            'name': self.name,
            'flag': self.flag,
            'value': self.value,
            'stolen': self.stolen is not None
        }

    def capture(self, team):
        if self.stolen is not None:
            Default.warning(
                'Team "%s" attempted to capture Flag "%s" owned by "%s" which is already captured by "%s"!'
                % (team.get_path(), self.get_path(), self.get_team().get_path(), self.stolen.get_path())
            )
            return None, False
        self.stolen = team
        transaction = new('TransactionFlag', False)
        transaction.flag = self
        transaction.value = self.value
        transaction.destination = team
        transaction.source = self.get_team()
        transaction.save()
        team.add_transaction(transaction)
        del transaction
        reverse = new('TransactionFlag', False)
        reverse.flag = self
        reverse.value = self.value * -1
        reverse.destination = team
        reverse.source = self.get_team()
        reverse.save()
        self.get_team().add_transaction(reverse)
        del reverse
        self.get_game().event('%s stole a Flag from %s!' % (self.stolen.get_name(), self.get_team().get_name()))
        Events.info('Flag "%s" owned by "%s" was captured by "%s"!' % (
            self.get_path(), self.get_team().get_path(), self.stolen.get_path()
        ))
        Default.info('Flag "%s" owned by "%s" was captured by "%s"!' % (
            self.get_path(), self.get_team().get_path(), self.stolen.get_path()
        ))
        self.save()
        hint = Flag.objects.get_next_flag(team)
        if hint is not None:
            return hint.description, True
        return None, True


class Host(Model):
    class Meta:
        verbose_name = '[Range] Host'
        verbose_name_plural = '[Range] Hosts'

    objects = HostManager()
    enabled = BooleanField('Host Enabled', default=True)
    name = SlugField('Host Nickname', max_length=64, null=True)
    status = BooleanField('Host Online', default=False, editable=False)
    scored = DateTimeField('Host Last Scored', null=True, editable=False)
    fqdn = CharField('Host Full Name', max_length=128, null=True, blank=True)
    ip = GenericIPAddressField('Host Address', protocol='both', unpack_ipv4=True)
    range = ForeignKey('scorebot_db.Range', on_delete=CASCADE, related_name='hosts')
    value = PositiveSmallIntegerField('Host Score Value', default=HOST_VALUE_DEFAULT)
    tolerance = PositiveSmallIntegerField('Host Ping Tolerance Percentage', null=True, blank=True)

    def clear(self):
        Default.info('Clearing Host "%s" and Services.' % self.get_path())
        self.scored = None
        for service in self.services.all():
            service.clear()
        for beacon in self.beacons.all():
            beacon.delete()
        for beacon in self.flags.all():
            beacon.delete()
        self.save()

    def __str__(self):
        team = self.get_team()
        if team is not None:
            return '[Host] %s (%d, %s): %s' % (self.fqdn, self.value, str(self.ip), team.get_path())
        return '[Host] %s (%d, %s)' % (self.fqdn, self.value, str(self.ip))

    def get_path(self):
        team = self.get_team()
        if team is not None:
            return '%s\\%s' % (team.get_path(), self.fqdn)
        return self.fqdn

    def get_game(self):
        return self.range.get_game()

    def get_team(self):
        return self.range.get_team()

    def __bool__(self):
        return self.beacons.all().count() == 0 and self.enabled

    def get_tolerance(self):
        return self.tolerance if self.tolerance is not None else int(self.get_game().get_setting('ping_tolerance'))

    def get_json(self, job=False):
        if job:
            return {
                'host': {
                    'fqdn': self.fqdn,
                    'services': [service.get_json(job) for service in self.services.all().filter(enabled=True)]
                },
                'dns': [str(dns.ip) for dns in self.range.dns.all()],
                'timeout': int(self.get_game().get_setting('job_timeout'))
            }
        return {
            'name': self.name,
            'fqdn': self.fqdn,
            'value': self.value,
            'status': self.status,
            'services': [service.get_json() for service in self.services.all().filter(enabled=True)]
        }

    def save(self, *args, **kwargs):
        if self.name is None and self.fqdn is not None:
            if '.' in self.fqdn:
                self.name = self.fqdn.split('.')[0]
            else:
                self.name = self.fqdn
        else:
            self.name = 'host-%s' % (str(self.ip).replace('.', '-').replace('/', ''))
        if self.name is not None and self.fqdn is None:
            self.fqdn = '%s.%s' % (self.name, self.range.domain)
        Model.save(self, *args, **kwargs)


class Range(Model):
    class Meta:
        verbose_name = '[Range] Range'
        verbose_name_plural = '[Range] Ranges'

    domain = CharField('Range Domain', max_length=64)
    subnet = CharField('Range Subnet', max_length=128)
    dns = ManyToManyField('scorebot_db.DNS', related_name='ranges')

    def clear(self):
        Default.info('Clearing Range "%s" and Hosts.' % self.get_path())
        for host in self.hosts.all():
            host.clear()
        self.save()

    def __str__(self):
        team = self.get_team()
        if team is not None:
            return '[Range] %s: %d (%s)' % (self.subnet, self.hosts.all().count(), team.get_path())
        return '[Range] %s: %d' % (self.subnet, self.hosts.all().count())

    def get_path(self):
        team = self.get_team()
        if team is not None:
            return '%s\\%s (%s)' % (team.get_path(), self.subnet, self.domain)
        return '%s (%s)' % (self.subnet, self.domain)

    def get_game(self):
        team = self.get_team()
        if team is not None:
            return team.get_game()
        return None

    def get_team(self):
        try:
            return self.team.filter(
                game__status=GAME_RUNNING, game__start__isnull=False, game__end__isnull=True
            ).first()
        except ObjectDoesNotExist:
            pass
        except MultipleObjectsReturned:
            raise ScorebotError('Range assigned to multiple Teams in running Games!')
        return None

    def get_json(self):
        return {
            'domain': self.domain,
            'network': self.subnet,
            'dns': [str(dns.ip) for dns in self.dns.all()],
            'hosts': [host.get_json() for host in self.hosts.all().filter(enabled=True)]
        }


class Beacon(Model):
    class Meta:
        verbose_name = '[Range] Beacon'
        verbose_name_plural = '[Range] Beacons'

    start = DateTimeField('Beacon Start', auto_now_add=True)
    end = DateTimeField('Beacon Finish', null=True, blank=True)
    update = DateTimeField('Beacon Last Update', null=True, blank=True)
    scored = DateTimeField('Beacon Last Scored', null=True, editable=False)
    token = ForeignKey('scorebot_db.Token', on_delete=CASCADE, related_name='beacons')
    owner = ForeignKey('scorebot_db.PlayingTeam', on_delete=CASCADE, related_name='beacons')
    host = ForeignKey('scorebot_db.Host', on_delete=CASCADE, related_name='beacons', null=True)
    ghost = ForeignKey('scorebot_db.BeaconHost', on_delete=CASCADE, related_name='beacons', null=True, blank=True)

    def score(self):
        if self.end is None and self.scored is None:
            transaction = new('TransactionBeacon', False)
            transaction.beacon = self
            transaction.destination = self.owner
            transaction.source = self.get_host().get_team()
            transaction.value = int(self.get_game().get_setting('beacon_score'))
            transaction.save()
            transaction.destination.add_transaction(transaction)
            reverse = new('TransactionBeacon', False)
            reverse.beacon = self
            reverse.destination = self.owner
            reverse.source = self.get_host().get_team()
            reverse.value = transaction.value * -1
            reverse.save()
            Default.info('Scored a Beacon by "%s" on Host "%s" owned by "%s" for "%d" PTS!' % (
                self.owner.get_path(), self.get_host().get_path(), transaction.source.get_path(), transaction.value
            ))
            transaction.source.add_transaction(reverse)
            del reverse
            del transaction
            self.scored = now()
            self.save()

    def expire(self):
        Default.info('Beacon by "%s" on Host "%s" has expired after "%d" seconds!' % (
            self.owner.get_path(), self.get_host().get_path(), self.__len__()
        ))
        Events.info('Beacon by "%s" on Host "%s" has expired after "%d" seconds!' % (
            self.owner.get_path(), self.get_host().get_path(), self.__len__()
        ))
        self.end = now()
        self.save()

    def __str__(self):
        return '[Beacon] %s -> %s (%s seconds)' % (
            self.owner.get_path(), self.get_host().get_team().get_path(), self.__len__()
        )

    def __len__(self):
        if self.update is not None:
            return (self.update - self.start).seconds
        return (now() - self.start).seconds

    def __bool__(self):
        return self.end is None

    def get_game(self):
        return self.owner.game

    def get_host(self):
        if self.ghost is not None:
            return self.ghost
        return self.host

    def get_path(self):
        return self.get_host().get_path()


class Service(Model):
    class Meta:
        verbose_name = '[Range] Service'
        verbose_name_plural = '[Range] Services'

    name = SlugField('Service Name', max_length=64)
    port = PositiveSmallIntegerField('Service Port')
    bonus = BooleanField('Service is Bonus', default=False)
    enabled = BooleanField('Service Enabled', default=True)
    host = ForeignKey('scorebot_db.Host', on_delete=CASCADE, related_name='services')
    bonus_enabled = BooleanField('Service Bonus Enabled', default=False, editable=False)
    application = SlugField('Service Application', max_length=64, null=True, blank=True)
    value = PositiveSmallIntegerField('Service Score Value', default=SERVICE_VALUE_DEFAULT)
    status = PositiveSmallIntegerField('Service Status', default=0, choices=SERVICE_STATUS)
    protocol = PositiveSmallIntegerField('Service Protocol', default=0, choices=SERVICE_PROTOCOLS)

    def clear(self):
        Default.info('Clearing Serivce "%s".' % self.get_path())
        self.status = 0
        self.bonus_enabled = False
        self.save()

    def __str__(self):
        return '[Service] %s\\%s %d/%s (%d%s) %s' % (
            self.host.get_path(), self.name, self.get_port(), self.get_protocol_display(), self.value,
            (', %s' % self.application if self.application is not None else ''), self.get_status_display()
        )

    def get_port(self):
        if self.port < 0:
            return self.port + 65534
        return self.port

    def get_path(self):
        return '%s\\%s' % (self.host.get_path(), self.name)

    def get_game(self):
        return self.host.get_game()

    def get_team(self):
        return self.host.get_team()

    def __bool__(self):
        if self.bonus and not self.bonus_enabled:
            return False
        return self.enabled

    def get_content(self):
        try:
            return self.content
        except AttributeError:
            pass
        return None

    def get_json(self, job=False):
        if job:
            return {
                'port': self.port,
                'application': self.application,
                'protocol': self.get_protocol_display(),
                'content': self.content.get_json(job) if self.get_content() is not None else None
            }
        return {
            'name': self.name,
            'bonus': self.bonus,
            'value': self.value,
            'port': self.get_port(),
            'application': self.application,
            'bonus_enabled': self.bonus_enabled,
            'status': self.get_status_display(),
            'protocol': self.get_protocol_display(),
            'content': self.content.get_json() if self.get_content() is not None else None
        }


class Content(Model):
    class Meta:
        verbose_name = '[Range] Service Content'
        verbose_name_plural = '[Range] Service Contents'

    format = CharField('Content Type', max_length=64)
    data = TextField('Content Data', null=True, blank=True)
    value = PositiveSmallIntegerField('Content Score Value', default=CONTENT_VALUE_DEFAULT)
    service = OneToOneField('scorebot_db.Service', on_delete=CASCADE, related_name='content')

    def __str__(self):
        return '[Content] %s (%s/%d)' % (self.service.get_path(), self.format, self.value)

    def get_game(self):
        return self.service.get_game()

    def get_team(self):
        return self.service.get_team()

    def get_json(self, job=False):
        if job:
            return {
                'type': self.format,
                'content': self.data
            }
        return {
            'value': self.value,
            'format': self.format
        }


class BeaconHost(Model):
    class Meta:
        verbose_name = '[Range] Beacon Host'
        verbose_name_plural = '[Range] Beacon Hosts'

    range = ForeignKey('scorebot_db.Range', on_delete=CASCADE, related_name='ghosts')
    ip = GenericIPAddressField('Beacon Host Address', protocol='both', unpack_ipv4=True)

    def __str__(self):
        return '[BeaconHost] %s: %s' % (str(self.ip), self.range.get_team().get_path())

    def get_path(self):
        return '%s\\%s' % (self.range.get_team().get_path(), str(self.ip))

    def get_game(self):
        return self.range.get_game()

    def get_team(self):
        return self.range.get_team()

# EOF
