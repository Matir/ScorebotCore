#!/usr/bin/python3

import json
import requests

a = requests.session()
a.headers['SBE-AUTH'] = '47d7ef30-ad31-4b2d-ae4b-f9f9ede284ed'


v = {"token": "9d1761be-b8c6-46f8-bbf7-aaf3a689fe79", "port": "4501"}

r = a.post('https://prosvjoes.com/api/beacon/port/', data=json.dumps(v))
print(r, r.status_code, r.content)

r = a.get('https://prosvjoes.com/api/beacon/port/') #, data=json.dumps(v))
print(r, r.status_code, r.content)


r = a.get('https://prosvjoes.com/api/mapper/1') #, data=json.dumps(v))
print(r, r.status_code, r.content)


"""
b = a.get('https://prosvjoes.com/api/beacon/')
try:
    c = b.content.decode('UTF-8')
except UnicodeDecodeError:
    c - str(b.content)

print('GOT: %d' % b.status_code)
d = None
try:
    d = json.loads(c)
    print(d)
    e = json.dumps(d, indent=4)
    print(e)
except json.JSONDecodeError:
    print(c)


if b.status_code == 201:
    d['host']['ping_sent'] = 10
    d['host']['ping_respond'] = 10
    e = json.dumps(d, indent=4)
    f = a.post('https://prosvjoes.com/api/job/', data=e)
    print(f.status_code, f.content)

    """