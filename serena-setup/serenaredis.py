#!/usr/bin/python

import socket,redis,time,sys

global r

def redis_connect():
	global r
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#result = sock.connect_ex(('127.0.0.1', 9080))
	result = sock.connect_ex(('serena.local', 6379))
	if result == 0:
		#r = redis.Redis(host='pub-redis-12138.us-central1-1-1.gce.garantiadata.com',
				#port=12138,
				#password='HelloWorldOfRedis',
				#db=0)
		r = redis.Redis(host='serena.local',
				port=6379,
				db=0)
		#r_check = r.get('ian') # A simple check for ian
		#if r_check == 'Hello':
		if r.ping():
			print "Redis Connected :)"
			return(0, '')
		else:
			return(1, 'SS: Err02\nNo Response!')
	else:
		return(1, 'SS: Err01')

def is_redis_available():
	global r
	try:
        	#r.get('ian')
        	r.ping()
	except (redis.exceptions.ConnectionError, redis.exceptions.BusyLoadingError):
        	return False
	return True

def redis_set_powerOn(siteInitials=None):
	global r
	index = 'serena:counter:system'
	if siteInitials:
		index += ':%s'% siteInitials
	#r.hincrby('serena:counter:system', 'powerOn', 1)
	r.hincrby(index, 'powerOn', 1)
	#print 'powerOn value: %s'% r.hget('serena:counter:system', 'powerOn')
	print 'powerOn value: [%s] %s'% (siteInitials, r.hget(index, 'powerOn'))
	

def redis_set_timeStamp(siteInitials=None):
	global r
	index = 'serena:counter:system'
	if siteInitials:
		index += ':%s'% siteInitials
	#r.hset('serena:counter:system', 'lastUpdate', int(time.time()))
	r.hset(index, 'lastUpdate', int(time.time()))
	#print 'Last timeStamp value: %s'% r.hget('serena:counter:system', 'lastUpdate')
	print 'Last timeStamp value: [%s]  %s'% (siteInitials, r.hget(index, 'lastUpdate'))


def redis_get_available_uuids():
	# We want to only make available non-active site uuids
	# so parse through them and only add non-active sites to the availableUuids dictionary
	availableUuids = {}
	uuids = redis_get_serena_databases()
	activeUuids = redis_get_active_serena_sites()
	#print 'Found the following uuids: %s'% uuids
	#print 'Found the following activeSites: %s'% activeUuids
	for key, value in uuids.items():
		if key not in activeUuids:
			availableUuids[key] = value
	#print 'Final availableUuids: %s'% availableUuids
	return availableUuids


def redis_get_active_serena_sites():
	global r, dbs
	#print "Got to redis_get_active_serena_sites"
	activeSites = []
	for active_site_uuid in r.scan_iter(match='active_uuids:*'):
		lastEpoch = r.hget(active_site_uuid, 'epoch')
		secondsAgo = int(time.time())-int(lastEpoch)
		key, site_uuid = active_site_uuid.split(':')
		#print 'Found an active site_uuid: %s, last active: %s [%s seconds ago]'% (site_uuid,lastEpoch,secondsAgo)
		activeSites.append(site_uuid)
	return activeSites;


def redis_get_serena_databases():
	global r, dbs
	#print "Got to redis_get_serena_databases"
	return r.hgetall('uuids');
	#return r.lrange('databases', 0, -1)


def redis_get_serena_site_config_v2(site_uuid):

	siteConfig={};

	sdb = redis.Redis(host='serena.local', port=6379, db=0)

	# Contacts - always defined as a hash in redis
	siteConfig['contacts']={}
	for key in sdb.scan_iter(site_uuid+":config:contacts:*"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			contact_id = key_split[-1]
			siteConfig['contacts'][contact_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['contacts'][contact_id][hkey] = value

	# Notification groups - always defined as a list in redis
	siteConfig['notifications']={}
	for key in sdb.scan_iter(site_uuid+":config:notificationGroups:*"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			ng_id = key_split[-1]
			siteConfig['notifications'][ng_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['notifications'][ng_id][hkey] = value

	# Triggers - always defind as a hash in redis
	siteConfig['triggers']={}
	for key in sdb.scan_iter(site_uuid+":config:triggers:*"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			trigger_id = key_split[-1]
			siteConfig['triggers'][trigger_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['triggers'][trigger_id][hkey] = value

	# Thresholds - always defind as a hash in redis
	siteConfig['thresholds']={}
	for key in sdb.scan_iter(site_uuid+":config:threshold:*"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			threshold_id = key_split[-1]
			siteConfig['thresholds'][threshold_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['thresholds'][threshold_id][hkey] = value

	# Startup options - always a hash
	siteConfig['options']={}
	for key in sdb.scan_iter(site_uuid+":config:startup"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Early warning options
	for key in sdb.scan_iter(site_uuid+":config:earlyWarning"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Alert options
	for key in sdb.scan_iter(site_uuid+":config:alert"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Redis options
	for key in sdb.scan_iter(site_uuid+":config:redis"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# siteInfo options
	for key in sdb.scan_iter(site_uuid+":config:siteInfo"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Sensors - always a hash
	siteConfig['sensors']={}
	for key in sdb.scan_iter(site_uuid+":config:sensors:*"):
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			sensor = key_split[-1]
			siteConfig['sensors'][sensor]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				siteConfig['sensors'][sensor][hkey] = value

	return (siteConfig)



#def redis_get_serena_site_config(db_index):
def redis_get_serena_site_config(site_uuid):
	global r, dbs
	#sdb = redis.Redis(host='pub-redis-12138.us-central1-1-1.gce.garantiadata.com',
				#port=12138,
				#password='HelloWorldOfRedis',
				#db=0)
	sdb = redis.Redis(host='serena.local',
				port=6379,
				db=0)
	# Contacts - always defined as a hash in redis
	contacts={}
	for key in sdb.scan_iter(site_uuid+":config:contacts:*"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			contact_id = key_split[-1]
			contacts[contact_id]={}
			print "Contact ID: %s"% contact_id
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				contacts[contact_id][hkey] = value
	print 'contacts: %s'% contacts

	# Notification groups - always defined as a list in redis
	notifications={}
	for key in sdb.scan_iter(site_uuid+":config:notificationGroups:*"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			ng_id = key_split[-1]
			notifications[ng_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				notifications[ng_id][hkey] = value

	#print notifications

	# Triggers - always defind as a hash in redis
	triggers={}
	for key in sdb.scan_iter(site_uuid+":config:triggers:*"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			trigger_id = key_split[-1]
			triggers[trigger_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				triggers[trigger_id][hkey] = value
	#print triggers

	# Thresholds - always defind as a hash in redis
	thresholds={}
	for key in sdb.scan_iter(site_uuid+":config:threshold:*"):
		#print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			threshold_id = key_split[-1]
			thresholds[threshold_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				#print '\tkey:%s, value: %s'% (hkey, value)
				thresholds[threshold_id][hkey] = value
	#print thresholds

	# Startup options - always a hash
	options={}
	for key in sdb.scan_iter(site_uuid+":config:startup"):
		#print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			options[option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				#print '\tkey:%s, value: %s'% (hkey, value)
				options[option_id][hkey] = value
	# Early warning options
	for key in sdb.scan_iter(site_uuid+":config:earlyWarning"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			options[option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				options[option_id][hkey] = value
	# Alert options
	for key in sdb.scan_iter(site_uuid+":config:alert"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			options[option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				options[option_id][hkey] = value
	# Redis options
	for key in sdb.scan_iter(site_uuid+":config:redis"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			options[option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				options[option_id][hkey] = value
	# siteInfo options
	print "Started siteInfo"
	for key in sdb.scan_iter(site_uuid+":config:siteInfo"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			options[option_id]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				options[option_id][hkey] = value
	print "Out of siteInfo"
	# Other Options
	#options['court']={}
	# Court Name
	#value = sdb.get("serena:config:courtName")
	#print 'key: %s value: %s'% ("serena:config:courtName", value)
	#options['court']['name']=value
	# Court Initials
	#value = sdb.get("serena:config:courtInitials")
	#print 'key: %s value: %s'% ("serena:config:courtInitials", value)
	#options['court']['initials']=value
	# Court Contact
	#value = sdb.get("serena:config:pointOfContact")
	#print 'key: %s value: %s'% ("serena:config:pointOfContact", value)
	#options['court']['poc']=value
	# Serena UUID
	#options['court']['uuid']=sdb.get("serena:config:uuid")
	# Redis Database
	#options['court']['RedisDB']=db_index

	print options

	# Sensors - always a hash
	sensors={}
	for key in sdb.scan_iter(site_uuid+":config:sensors:*"):
		print 'key: %s [%s]'% (key, sdb.type(key))
		if sdb.type(key) == 'hash':
			key_split= key.split(':')
			sensor = key_split[-1]
			sensors[sensor]={}
			for hkey in sdb.hgetall(key):
				value = sdb.hget(key, hkey)
				print '\tkey:%s, value: %s'% (hkey, value)
				sensors[sensor][hkey] = value
	#print sensors

	return (contacts, notifications, thresholds, options, sensors, triggers)

# For testing this python code
#redis_connect()
#redis_set_powerOn()
#redis_set_timeStamp()
#print 'powerOn value: %s'% r.hget('serena:counter:system', 'powerOn')
#print 'Last timeStamp value: %s'% r.hget('serena:counter:system', 'lastUpdate')
#print 'testing redis_get_serena_site_config\n'
#print redis_get_serena_site_config(1)

