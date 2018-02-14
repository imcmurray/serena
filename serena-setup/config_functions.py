import time, os, subprocess, ConfigParser, logging, redis

# Will only create a config.yaml file if serena.local requires it (updated information)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def getMAC(interface):
	# Return the MAC address of interface
	try:
		str=open('/sys/class/net/'+interface+'/address').read()
	except:
		str="00:00:00:00:00:00"
	return str[0:17]


def check_valid_site(site_uuid):
	r = redis.Redis(host='serena.local', port=6379, db=0)
	return(r.hexists('uuids',site_uuid))


def clear_update_flag(site_uuid):
	r = redis.Redis(host='serena.local', port=6379, db=0)
	r.hset(site_uuid+':config:device','update_required', None,)
	r.hset(site_uuid+':config:device','last_updated', int(time.time()))


def get_update_flag(site_uuid):
	r = redis.Redis(host='serena.local', port=6379, db=0)
	return(r.hget(site_uuid+':config:device','update_required'))


def set_mac_address(site_uuid):
	r = redis.Redis(host='serena.local', port=6379, db=0)
	return(r.hset(site_uuid+':config:device','mac_address', getMAC('eth0')))


def get_site_config(site_uuid):
	r = redis.Redis(host='serena.local', port=6379, db=0)
	siteConfig={};

	# Contacts - always defined as a hash in redis
	siteConfig['contacts']={}
	for key in r.scan_iter(site_uuid+":config:contacts:*"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			contact_id = key_split[-1]
			siteConfig['contacts'][contact_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['contacts'][contact_id][hkey] = value

	# Notification groups - always defined as a list in redis
	siteConfig['notifications']={}
	for key in r.scan_iter(site_uuid+":config:notificationGroups:*"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			ng_id = key_split[-1]
			siteConfig['notifications'][ng_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['notifications'][ng_id][hkey] = value

	# Triggers - always defind as a hash in redis
	siteConfig['triggers']={}
	for key in r.scan_iter(site_uuid+":config:triggers:*"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			trigger_id = key_split[-1]
			siteConfig['triggers'][trigger_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['triggers'][trigger_id][hkey] = value

	# Thresholds - always defind as a hash in redis
	siteConfig['thresholds']={}
	for key in r.scan_iter(site_uuid+":config:threshold:*"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			threshold_id = key_split[-1]
			siteConfig['thresholds'][threshold_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['thresholds'][threshold_id][hkey] = value

	# Startup options - always a hash
	siteConfig['options']={}
	for key in r.scan_iter(site_uuid+":config:startup"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Early warning options
	for key in r.scan_iter(site_uuid+":config:earlyWarning"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Alert options
	for key in r.scan_iter(site_uuid+":config:alert"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Redis options
	for key in r.scan_iter(site_uuid+":config:redis"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# siteInfo options
	for key in r.scan_iter(site_uuid+":config:siteInfo"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			option_id = key_split[-1]
			siteConfig['options'][option_id]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['options'][option_id][hkey] = value

	# Sensors - always a hash
	siteConfig['sensors']={}
	for key in r.scan_iter(site_uuid+":config:sensors:*"):
		if r.type(key) == 'hash':
			key_split= key.split(':')
			sensor = key_split[-1]
			siteConfig['sensors'][sensor]={}
			for hkey in r.hgetall(key):
				value = r.hget(key, hkey)
				siteConfig['sensors'][sensor][hkey] = value

	return (siteConfig)


def write_config_no_update_required(site_uuid):

	logger.info('Entered write_config_no_update_required')
	logger.info('Site UUID: %s', site_uuid)
	configfile_name = "/home/pi/Serena/serena-setup/config.yaml"

	logger.info('Updating regardless of if serena.local says so!')


	# remove configfile_name before we start anything
	if os.path.isfile(configfile_name):
		os.remove(configfile_name)
		logger.info('configuration file: %s removed', configfile_name)

	siteConfig = get_site_config(site_uuid)

	#print 'siteConfig contains:\n%s'% siteConfig
	logger.info('siteConfig: %s', siteConfig)

	# Check if there is already a configurtion file
	if not os.path.isfile(configfile_name):

		# Create the configuration file as it doesn't exist yet
		cfgfile = open(configfile_name, 'w')

		# Add content to the file
		Config = ConfigParser.ConfigParser()
		groups = {};

		for key in siteConfig.keys():
			logger.info('Working on [%s]', key)
			groups[key] = []
			for keya in siteConfig[key].keys():
				groups[key].append(key+'-'+keya)
				Config.add_section(key+'-'+keya)
				for keyb in siteConfig[key][keya].keys():
					logger.info('\t\t[%s] = [%s]', keyb, siteConfig[key][keya][keyb])
					if siteConfig[key][keya][keyb]:
						Config.set(key+'-'+keya, keyb, siteConfig[key][keya][keyb])

		Config.add_section('identifiers')

		for key in siteConfig.keys():
			Config.set('identifiers', key, groups[key])

		logger.info('Writing configuration to: %s', configfile_name)
		Config.write(cfgfile)
		cfgfile.close()
		logger.info('Done')

	if not os.path.isfile(configfile_name):
		logger.error('Unable to write configuration file')
		return(1)
	else:
		logger.info('Configuration written')
		# clear the update flag on serena.local
		clear_update_flag(site_uuid)
		set_mac_address(site_uuid)
		return(0)



def write_config_if_update_required(site_uuid):

	logger.info('Entered write_config_if_update_required')
	logger.info('Site UUID: %s', site_uuid)
	configfile_name = "/home/pi/Serena/serena-setup/config.yaml"

	# Does serena.local have any updates? (serena.local:[{site_uuid}:conf:device[update_required:{None/1}]])
	need_to_update = get_update_flag(site_uuid)
	logger.info('Updated required? [%s]', need_to_update)

	if need_to_update == '1':

		logger.info('Yes- we must update the local configuration')

		# remove configfile_name before we start anything
		if os.path.isfile(configfile_name):
			os.remove(configfile_name)
			logger.info('configuration file: %s removed', configfile_name)

		siteConfig = get_site_config(site_uuid)

		#print 'siteConfig contains:\n%s'% siteConfig
		logger.info('siteConfig: %s', siteConfig)

		# Check if there is already a configurtion file
		if not os.path.isfile(configfile_name):

			# Create the configuration file as it doesn't exist yet
			cfgfile = open(configfile_name, 'w')

			# Add content to the file
			Config = ConfigParser.ConfigParser()
			groups = {};

			for key in siteConfig.keys():
				logger.info('Working on [%s]', key)
				groups[key] = []
				for keya in siteConfig[key].keys():
					groups[key].append(key+'-'+keya)
					Config.add_section(key+'-'+keya)
					for keyb in siteConfig[key][keya].keys():
						logger.info('\t\t[%s] = [%s]', keyb, siteConfig[key][keya][keyb])
						if siteConfig[key][keya][keyb]:
							Config.set(key+'-'+keya, keyb, siteConfig[key][keya][keyb])

			Config.add_section('identifiers')

			for key in siteConfig.keys():
				Config.set('identifiers', key, groups[key])

			logger.info('Writing configuration to: %s', configfile_name)
			Config.write(cfgfile)
			cfgfile.close()
			logger.info('Done')

		if not os.path.isfile(configfile_name):
			logger.error('Unable to write configuration file')
			return(1)
		else:
			logger.info('Configuration written')
			# clear the update flag on serena.local
			clear_update_flag(site_uuid)
			return(0)
	else:
		logger.info('No update required')

	exit()




#if __name__ == '__main__':
	#siteUUID='4cde46b5-72d9-4dfc-a1f1-8372dd9a33ce'
	#write_config(siteUUID)

