#!/usr/bin/false
#
# Scorebotv4 - The Scorebot Project
# 2018 iDigitalFlame / The Scorebot / CTF Factory Team
#
# Djano API Views Utilities

from random import choice
from json import dumps  # , loads
from scorebot.util import authenticate, ip
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from scorebot import General, Authentication, Jobs, HTTP_GET, HTTP_POST
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from scorebot_db.models import AssignedMonitor, Job, PlayerTeam, Flag, Host, \
                               Port, Game, Service, Content, Purchase, Item
from scorebot.constants import JOB_MESSAGE_NO_HOSTS, MESSAGE_INVALID_METHOD, MESSAGE_MISSING_FIELD, \
                               FLAG_MESSAGE_STOLEN, FLAG_MESSAGE_NOT_EXIST, FLAG_MESSAGE_HINT, TEAM_MESSAGE_TOKEN, \
                               TEAM_MESSAGE_PORT_LIST, GAME_RUNNING
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponse, HttpResponseNotFound, \
                        HttpResponseServerError, HttpResponseRedirect


@csrf_exempt
@authenticate()
def job(request):
    client = ip(request)
    games, monitor, err = AssignedMonitor.objects.get_montiors(client, request.auth)
    if err is not None:
        return err
    if request.method == HTTP_GET:
        Authentication.debug('[%s] AssignedMonitor "%s" connected to request a Job, assigned to "%d" running Games.' % (
            client, monitor.name, len(games)
        ))
        General.info('[%s] AssignedMonitor "%s" connected to request a Job, assigned to "%d" running Games.' % (
            client, monitor.name, len(games)
        ))
        Jobs.debug('[%s] AssignedMonitor "%s": Connected and will attempt to pick "%d" times for a valid Job.' % (
            client, monitor.name, len(games)
        ))
        for game_num in range(0, len(games)):
            game = choice(games)
            Jobs.debug('[%s] AssignedMonitor "%s": Selection round "%s" selected Game "%s".' % (
                client, monitor.name, game_num, game.game.get_name()
            ))
            job = Job.objects.new_job(game)
            if job is not None:
                Jobs.info('[%s] AssignedMonitor "%s": Job ID "%d" created for Host "%s"!' % (
                    client, monitor.name, job.id, job.host.get_path()
                ))
                return HttpResponse(status=201, content=dumps(job.get_json(), indent=4))
            del game
        del games
        Jobs.debug('[%s] AssignedMonitor "%s": Has no valid hosts to choose from!' % (client, monitor.name))
        return HttpResponse(status=204, content=JOB_MESSAGE_NO_HOSTS)
    elif request.method == HTTP_POST:
        return Job.objects.get_job(monitor, request)
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@csrf_exempt
@authenticate()
def flag(request):
    if request.method == HTTP_POST:
        team, data, _, err = PlayerTeam.objects.get_team_json(request, field='token', offensive=True)
        if err is not None:
            return err
        client = ip(request)
        if 'flag' not in data:
            General.error('[%s] Client attempted to submit a Flag without the "flag" value!' % client)
            return HttpResponseBadRequest(content=MESSAGE_MISSING_FIELD.format(field='flag'))
        flag = Flag.objects.get_flag_query(team, data['flag'])
        del data
        if flag is None:
            General.error('[%s] Team "%s" attempted to submit a Flag that does not exist!' % (
                client, team.get_path()
            ))
            return HttpResponseNotFound(content=FLAG_MESSAGE_NOT_EXIST)
        if flag.stolen is not None:
            General.error('[%s] Team "%s" attempted to submit a Flag "%s" that was already captured!' % (
                client, team.get_path(), flag.get_path()
            ))
            return HttpResponse(status=204, content=FLAG_MESSAGE_STOLEN)
        hint, captured = flag.capture(team)
        if not captured:
            General.error('[%s] Team "%s" attempted to submit a Flag "%s" that was already captured!' % (
                client, team.get_path(), flag.get_path()
            ))
            return HttpResponse(status=204, content=FLAG_MESSAGE_STOLEN)
        return HttpResponse(status=200, content=FLAG_MESSAGE_HINT.format(hint=str(hint)))
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@csrf_exempt
@authenticate()
def beacon(request):
    if request.method == HTTP_POST:
        team, data, token, err = PlayerTeam.objects.get_team_json(request, field='token', offensive=True, beacon=True)
        if err is not None:
            return err
        client = ip(request)
        if 'address' not in data:
            General.error('[%s] Client attempted to submit a Beacon without the "address" value!' % client)
            return HttpResponseBadRequest(content=MESSAGE_MISSING_FIELD.format(field='address'))
        return Host.objects.get_beacon(team, token, data['address'])
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@csrf_exempt
@authenticate()
def register(request):
    if request.method == HTTP_POST:
        team, _, _, err = PlayerTeam.objects.get_team_json(request, field='token', offensive=True)
        if err is not None:
            return err
        General.debug('[%s] Client requested a Beacon Token for "%s".' % (ip(request), team.get_path()))
        return HttpResponse(status=201, content=TEAM_MESSAGE_TOKEN.format(token=str(team.add_beacon_token().uid)))
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@csrf_exempt
@authenticate()
def ports(request):
    if request.method == HTTP_GET:
        return HttpResponse(content=TEAM_MESSAGE_PORT_LIST.format(list=','.join(Port.objects.get_list())))
    elif request.method == HTTP_POST:
        team, data, _, err = PlayerTeam.objects.get_team_json(request, field='token', offensive=True)
        if err is not None:
            return err
        if 'port' not in data:
            General.error('[%s] Client attempted to open a Beacon Port without the "port" value!!' % ip(request))
            return HttpResponseBadRequest(content=MESSAGE_MISSING_FIELD.format(field='port'))
        return Port.objects.get_port(team, data['port'])
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@authenticate()
def mapper(request, gid):
    if request.method == HTTP_GET:
        General.debug('[%s] Client is request UUID mappings for Game ID "%s"!' % (ip(request), gid))
        try:
            game = Game.objects.get(id=int(gid), status=GAME_RUNNING)
        except (ObjectDoesNotExist, MultipleObjectsReturned, ValueError):
            return HttpResponseNotFound()
        return HttpResponse(status=200, content=dumps(game.get_team_list()))
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@authenticate('__SYS__STORE')
def purchase(request, team_id=None):
    """Run a purchase.

    """
    if request.method == METHOD_POST:
	try:
	    decoded_data = request.body.decode('UTF-8')
	except UnicodeDecodeError:
	    api_error('STORE', 'Data submitted is not encoded properly!', request)
	    return HttpResponseBadRequest(content='{"result": "SBE API: Incorrect encoding, please use UTF-8!"}')
	try:
	    json_data = json.loads(decoded_data)
	except json.decoder.JSONDecodeError:
	    api_error('STORE', 'Data submitted is not in correct JSON format!', request)
	    return HttpResponseBadRequest(content='{"result": "SBE API: Not in a valid JSON format!"]')
	if 'team' not in json_data or 'order' not in json_data:
	    api_error('STORE', 'Data submitted is missing JSON fields!', request)
	    return HttpResponseBadRequest(content='{"result": "SBE API: Not in a valid JSON format!"}')
	try:
	    team = PlayerTeam.objects.get(store=int(json_data['team']), game__status=GAME_RUNNING)
	except ValueError:
	    api_error('STORE', 'Attempted to use an invalid Team ID "%s"!' % str(team_id), request)
	    return HttpResponseNotFound('{"result": "SBE API: Invalid Team ID!"}')
	except ObjectDoesNotExist:
	    api_error('STORE', 'Attempted to use an non-existent Team ID "%s"!' % str(team_id), request)
	    return HttpResponseNotFound('{"result": "SBE API: Team could not be found!"}')
	except MultipleObjectsReturned:
	    api_error('STORE', 'Attempted to use a Team ID which returned multiple Teams!', request)
	    return HttpResponseNotFound('{"result": "SBE API: Team could not be found!"}')
	api_info('STORE', 'Attempting to add Purchase records for Team "%s".' % team.get_canonical_name(), request)
	if not isinstance(json_data['order'], list):
	    api_error('STORE', 'Data submitted is missing the "order" array!', request)
	    return HttpResponseBadRequest(content='{"result": "SBE API: Not in valid JSON format!"}')
	purchase = Purchase()
	purchase.source = team
	purchase.destination = team.game.gold
	purchase.value = 0
	for order in json_data['order']:
            try:
                purchase.value += int(order['price'])
                # This needs to be an item object
                item = Item()
                item.purchase = purchase
                item.name = (order['item'] if len(order['item']) < 150 else order['item'][:150])
                item.sid = order['id']
                api_score(team.id, 'PURCHASE', team.get_canonical_name(), purchase.amount, purchase.item)
                api_debug('STORE', 'Processed order of "%s" "%d" for team "%s"!'
                            % (purchase.item, purchase.amount, team.get_canonical_name()), request)
            except ValueError:
                api_warning('STORE', 'Order "%s" has invalid integers for amount!!' % str(order), request)
        purchase.save()
        for i in purchase.items:
            i.save()
	return HttpResponse(status=200, content='{"result": "processed"}')
    return HttpResponseBadRequest(content='{"result": "SBE API: Not a supported method type!"}')


@authenticate('__SYS__STORE')
def transfer(request):
    pass


def scoreboard(request, gid):
    if request.method == HTTP_GET:
        try:
            game = Game.objects.get(id=int(gid), status=GAME_RUNNING)
        except (ObjectDoesNotExist, MultipleObjectsReturned, ValueError):
            return HttpResponseNotFound()
        return HttpResponse(status=200, content=dumps(game.get_scoreboard(True)))
    return HttpResponseBadRequest(content=MESSAGE_INVALID_METHOD)


@authenticate()
def token_check(request):
    try:
	token = request.auth
    except AttributeError:
	return HttpResponseForbidden(content='SBE API: No authentication!')
    resp = {
	    'token': str(token.uuid),
	    'permissions': token.permission_strings(),
	    }
    return JsonResponse(resp)


@csrf_exempt
@authenticate('__SYS_STORE')
def new_resource(request):
    """Create a new monitored resource.

	Requires a JSON post with the following fields:

	team: A valid game team id
	host: A dictionary of the host, containing:
	    name: Display name for the host.
	    fqdn: FQDN for the host to be scored.
	services: An array of dictionary definition of the services on the host, containing:
	    port: Integer port for the service
	    name: String name for the service
	    bonus: Boolean if service is bonus (optional)
	    value: Integer scoreable value (optional)
	    protocol: 'tcp', 'udp', 'icmp' (optional, default 'tcp')
	    content: string or dictionary to store as scorebot_grid.Content (optional)
    """
    if request.method != METHOD_POST:
	return HttpResponseBadRequest(content='{"result": "SBE API: Not a supported method type!"}')
    try:
	decoded_data = request.body.decode('UTF-8')
    except UnicodeDecodeError:
	api_error('NEW_RESOURCE', 'Data submitted is not encoded properly!', request)
	return HttpResponseBadRequest(content='{"result": "SBE API: Incorrect encoding, please use UTF-8!"}')
    try:
	json_data = json.loads(decoded_data)
    except json.decoder.JSONDecodeError:
	api_error('NEW_RESOURCE', 'Data submitted is not in correct JSON format!', request)
	return HttpResponseBadRequest(content='{"result": "SBE API: Not in a valid JSON format!"]')
    try:
	team = PlayerTeam.objects.get(store=int(json_data['team']), game__status=GAME_RUNNING)
    except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned):
	api_error('NEW_RESOURCE', 'Attempted to use an invalid Team ID "%s"!' % str(team_id), request)
	return HttpResponseNotFound('{"result": "SBE API: Invalid Team ID!"}')
    new_host = Host()
    try:
	new_host.fqdn = json_data['host']['fqdn']
	new_host.name = json_data['host']['name']
	new_host.team = team
    except KeyError:
	api_error('NEW_RESOURCE', 'Invalid JSON for new host!')
	return HttpResponseBadRequest(content='{"result": "SBE API: Invalid JSON for new host!')
    if 'services' not in json_data:
	api_error('NEW_RESOURCE', 'Invalid JSON for new host!')
	return HttpResponseBadRequest(content='{"result": "SBE API: Invalid JSON for new host!')
    services = []
    for svc_data in json_data['services']:
	new_service = Service()
	try:
		new_service.port = int(svc_data['port'])
		new_service.name = svc_data['name']
		new_service.bonus = svc_data.get('bonus', False)
		new_service.value = svc_data.get('value', new_service.value)
		protocol = svc_data.get('protocol', 'tcp')
		found = False
		for k, v in SERVICE_PROTOCOLS:
		    if v == protocol:
			new_service.protocol = k
			found = True
			break
		if not found:
		    raise ValueError('Invalid protocol: ' + protocol)
	except (KeyError, ValueError):
	    api_error('NEW_RESOURCE', 'Invalid JSON for new service!')
	    return HttpResponseBadRequest(content='{"result": "SBE API: Invalid JSON for new service!')
	if 'content' in svc_data:
	    try:
		content = svc_data['content']
		if isinstance(content, dict):
		    content = dumps(content)
		new_service.content = Content(data=content)
	    except (KeyError, ValueError):
		api_error('NEW_RESOURCE', 'Invalid JSON for new service!')
		return HttpResponseBadRequest(content='{"result": "SBE API: Invalid JSON for new service!')
	services.append(new_service)
    # Save all the new data
    new_host.save()
    for new_service in services:
	if new_service.content:
	    new_service.content.save()
	new_service.host = new_host
	new_service.save()
    return HttpResponse(status=200, content='{result: "Created"}')
# EOF
