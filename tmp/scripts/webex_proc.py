#!/usr/bin/python3

# Sample script to update Cisco KMS syslog records in elastic and add human readable
# user information. 
#
# Syslog messages received from Cisco Hybrid Data Security (HDS) contain only user
# representations based on UUIDs. To provide more detailed human readable information
# that can be used in ELK dashboards the scripts queries syslog records in ELK that 
# are missing user information and extracts the UUIDs.
# The sciprt will next check if a given UUID is already present in ELK from earlier 
# run. In this case the existing UUID-> user information is applied to the syslog record.
# In case the user information is not available in ELK the Cisco Webex API is authomatically
# quried to retrieve the required information from the cloud.
#
# Script requires a client_id, client_secret, refresh_token which can be optained from 
# developer.webex.com
#
# This sample script is provided as is. Cisco Systems does not provide any warranty or
# support. It is not intended for production deployment. Use at your own risk.


import sys
import os
import operator
import requests
import json
import codecs
import time
import logging
from collections import OrderedDict
from operator import itemgetter

access_token_file = "/tmp/scripts/webex_teams_proc.token"

log_level = "logging.DEBUG"
log_file = "/var/log/webex_proc.log"

def get_KMS_requests():
	url = 'http://elk:9200/_search?pretty=true'
	data =  '''{
            "_source": [
                "hdsuserID"
            ],
            "size": 10000,
            "query": {
                "constant_score": {
                    "filter": {
                        "bool": {
                            "must": {
                                "match": {
                                    "hdsaction": {
                                        "query": "KMS:REQUEST",
                                        "type": "phrase"
                                    }
                                }
                            },
                            "must_not": [
                                {"exists": {"field": "userinfo.created"}},
                                {"match":{"hdsuserID":"null"}}
                                ]
                            }
                        }
                    }
                }
            }'''
	response = requests.get(url,data = data)
	jResp = json.loads(response.content.decode('utf-8'))
	return jResp 

def get_access_token(refresh_tok,cltID,cltSec):
	url = 'https://api.ciscospark.com/v1/access_token'
	response = requests.post( url, {
                                 'refresh_token': refresh_tok,
                                 'grant_type': 'refresh_token',
                                 'client_id': cltID,
                                 'client_secret': cltSec
                                 })
	jResp = json.loads(response.content.decode('utf-8'))
	print('DEBUG: Access Token Fetch', jResp)
	resp = {}
	if 'access_token' in jResp:
		resp['token'] = jResp['access_token']
	if 'expires_in' in jResp:
		resp['expires_in'] = jResp['expires_in']
		resp['timestamp'] = time.time()
	return resp

def get_user_info_elastic(useruuid):
	url = 'http://elk:9200/_search'
	response = requests.post( url, headers={ 'Content-Type': 'application/json' },
				data=json.dumps({
    					'_source': ['userinfo'],
					'from' : 0, 'size' : 1,
					'query': {
				   		'bool': {
				      			'must': [
					 			{ 'match': { 'hdsuserID': {
										'query': useruuid,
										'type': 'phrase'
							    			}
									}
								},
								{ 'exists': { 'field': 'userinfo' }
								}
				      			]
				    		}
					}
				}) )
	jResp = json.loads(response.content.decode('utf-8'))
	resp = {}
	# print( "Result REST get_user_elastic: ", jResp )
        # check if uuid already in elastic - number of hits returnes > 0
	if jResp['hits']['total'] > 0:
		# get userinfo 
		if 'userinfo' in jResp['hits']['hits'][0]['_source']:
			resp['userinfo'] = jResp['hits']['hits'][0]['_source']['userinfo']
			# print("Returned userinfo object get_user_elastic: ", resp)
			return resp
	else:
		return False

def get_user_info_webex(useruuid, authtoken):
	url = 'https://api.ciscospark.com/v1/people/'+useruuid
	auth = 'Bearer ' + authtoken
	# print( "DEBUG: Webex Teams API lookup URL & access token: ", url, auth )
	logging.debug('Webex API lookup URL & access token: %s %s ', url, auth )
	response = requests.get ( url, headers={
					'Content-Type': 'application/json',
					'Authorization': auth
				})
	if response.status_code == 200: 
		jResp = json.loads(response.content.decode('utf-8'))
		resp = {}
		resp['userinfo'] = jResp
		# print( "DEBUG: Result 200 OK REST get_user_info_webex: ", resp['userinfo'] )
		logging.debug('Result 200 OK REST get_user_info_webex : %s ', resp['userinfo'] )
	else:
		print( "DEBUG: Result REST get_user_info_webex (raw) something went wrong: ", response )
		input("Press Enter to Continue...")

	return resp

def update_userinfo(userinfo, new_uinfo):
	url = 'http://elk:9200/' + userinfo['_index'] + '/CiscoHDS/' + userinfo['_id']+ '/_update'
	# print( "DEBUG: update_userinfo URL: ", url )
	# print( "DEBUG: update_userinfo new user information: ", new_uinfo['userinfo'] )
	logging.debug('updare_userinfo new user information: %s ', new_uinfo['userinfo'] )
	reponse = requests.post( url, headers={ 'Content-Type': 'application/json' },
                                data=json.dumps( {
				  	"doc": { "userinfo": new_uinfo['userinfo'] }
				} ) )
	jResp = json.loads(reponse.content.decode('utf-8'))
	resp = {}
	# print( "update_userinfo URL REST reponse: ", jResp )
	logging.debug('update_userinfo URL REST response: %s ', jResp )
	return

logging.basicConfig(filename=log_file,level=logging.DEBUG)

logging.debug('This message should go to the log file')

try:
	# open token file 
	access_token_f = open(access_token_file, 'r')
except FileNotFoundError:
	# get new access token from webex API
	access = get_access_token( refresh_token, client_id, client_secret)
	print( 'Access Token: ', access)
	logging.debug('access token: ', access)
	# no access token on file, open file for write
	access_token_f = open(access_token_file,'w')
	# for testing define access token manual without call to webex API
	# access = json.dumps( {'expires_in': 1209599, 'token': 'YzJhYzUtNGM0OS00ZmM5LTk1YTUtMzk5OGRkZjQ3NzdmYTRiOTJiNTgtM2E3', 'timestamp': 1496069706.3693337} )
	# write token
	access_token_f.write( json.dumps(access) )
	# pos = access_token_f.tell()
	# print(" position: ", pos)
	# pos = access_token_f.seek(0,0)
	# access_token_f.write( access )
	access_token_f.close()
else:
	# read json object from access token file 
	access = json.loads( access_token_f.read())
	logging.debug('Access token file exists' )
	logging.debug('Token: %s ', access["token"] )
	logging.debug('Expires in: %s ', access["expires_in"] )
	logging.debug('Timestamp: %s', access["timestamp"] )
	# check if token read from file has expired
	if access["timestamp"] + access["expires_in"] < time.time() - 180:
		# call webex API to get new token
		access = get_access_token( refresh_token, client_id, client_secret)
		# write new access token to file
		access_token_f = open(access_token_file,'w')
		pos = access_token_f.seek(0,0)
		access_token_f.write( access )
		logging.debug('New access token written to file on startup... %s ', access )
		access_token_f.close()

# access = get_access_token( refresh_token, client_id, client_secret)
# logging.debug('main get access token: %s ', access )

lo_time_stamp = time.time ()

while  True:
	# check if we need no auth_token
	if access["timestamp"] + access["expires_in"] < time.time() - 180:
		access = get_access_token( refresh_token, client_id, client_secret)
		# write new access token to file
		access_token_f = open(access_token_file,'w')
		pos = access_token_f.seek(0,0)
		access_token_f.write( access )
		access_token_f.close()
		logging.debug('got new access token & wrote to file: %s ', access)
	# run this every 10 sec 
	if time.time() > lo_time_stamp + 10:
		jResponse = get_KMS_requests()
		lo_time_stamp = time.time()

		logging.debug('Total number of hits in search: %s ',  jResponse['hits']['total'])

		records_updated = 0
		count = 0 
		for userid in jResponse["hits"]["hits"]:
			# logging.debug('search result: %s ', userid)
			# check for broken records with no hdsuserID field
			if 'hdsuserID' in userid["_source"]:
				# more housekeeping for empty records
				if userid["_source"]["hdsuserID"] == 'null': continue
				if userid["_source"]["hdsuserID"]:
					logging.debug('checking userinfo already in elastic: %s ', userid["_source"]["hdsuserID"] )
					uinfo = get_user_info_elastic( userid["_source"]["hdsuserID"] )
					if not uinfo:
						# print( "DEBUG: No entry in elastic: ", userid["_source"]["hdsuserID"] )
						logging.debug('No entry in elastic: %s ', userid["_source"]["hdsuserID"] )
						uinfo = get_user_info_webex( userid["_source"]["hdsuserID"], access["token"] )
						# print( "DEBUG: Fetched entry from webex cloud: ", uinfo )
						logging.debug('Fetched entry from webex cloud: %s ', uinfo )
					# print( "DEBUG: execute main loop update: ", userid["_index"], userid["_id"])
					logging.debug('execute main loop update: %s - %s', userid["_index"], userid["_id"])
					update_userinfo( userid, uinfo )
					records_updated  += 1
			count += 1
		# print( "DEBUG: records updated: ", records_updated )
		logging.debug('records updated: %s ', records_updated )
		logging.debug('count: %s ', count)
#	else:
#		print("Broken record !!! ", userid["_source"])
