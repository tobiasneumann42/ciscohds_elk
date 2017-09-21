import requests
import json
import uuid
import time

headers = {
    'Authorization' : 'Bearer <bearer from developer.ciscospark.com goes here>',
    'Content-Type' : 'application/json'
    }

base = 'https://api.ciscospark.com/v1'

# who am I?
r = requests.get('https://api.ciscospark.com/v1/people/me', headers=headers)
r.raise_for_status()
me_id = r.json()['id']

# get all people
r = requests.get('https://api.ciscospark.com/v1/people', params={'max':1000}, headers=headers)
r.raise_for_status()
people = [p for p in r.json()['items'] if p.get('invitePending') == False]

print('Found {} people: {}'.format(len(people), ', '.join((p['displayName'] for p in people))))
while True:
    # create random rooms will all people
    r = requests.post('https://api.ciscospark.com/v1/rooms', headers=headers, data=json.dumps({'title' : 'zz auto generated {}'.format(str(uuid.uuid4()))}))
    r.raise_for_status()
    space_id = r.json()['id']
    
    # add people to that space
    for p in (p for p in people if p['id'] != me_id):
        r = requests.post('https://api.ciscospark.com/v1/memberships', headers=headers, data=json.dumps({'isModerator' : True, 'roomId' : space_id, 'personId' : p['id']}))
        r.raise_for_status()
    
    # finally post a message to that space
    r = requests.post('https://api.ciscospark.com/v1/messages', headers=headers, data=json.dumps({'roomId' : space_id, 'text' : 'Space automatically created to cause some traffic'}))
    
    time.sleep(30)
