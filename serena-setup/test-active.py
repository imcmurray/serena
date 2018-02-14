import time, sys, os, subprocess
import serenaredis



def reset():
	print "Hit reset!"
        sys.exit()

def select_instance(dbs):
	picked_db=-1
	databases=[]
	num_of_dbs = len(dbs)
	print 'Found %s databases'% num_of_dbs
	b = int(1024/num_of_dbs)
	for k,v in sorted(dbs.items()):
		for c in range (0,b):
			databases.append(k)
        while len(databases) <= 1024:
		# top up databases so all the 1024 range is covered for the dial
                databases.append(sorted(dbs.keys())[-1])
	while picked_db == -1:
		s_value = grovepi.analogRead(selector)
		if ( dbs[databases[s_value]] ) :
			print "%d | %s | %s "% (int(s_value), databases[s_value], dbs[databases[s_value]])
			site_name = '{:<10}'.format(dbs[databases[s_value]][:10])
			txt = 'Site: {:s}\n{:16s}'.format(site_name, databases[s_value])
			setText_norefresh(txt)
		if int(grovepi.digitalRead(button)):
			picked_db=s_value
			return (0,dbs[databases[s_value]],databases[s_value])

def write_config(site_uuid):
	configfile_name = "config.yaml"
	print "got to write_config with site_uuid of: %s\n"% site_uuid

	contacts, notifications, thresholds, options, sensors, triggers = serenaredis.redis_get_serena_site_config(site_uuid)

	# Check if there is already a configurtion file
	if not os.path.isfile(configfile_name):
		# Create the configuration file as it doesn't exist yet
		cfgfile = open(configfile_name, 'w')

		# Add content to the file
		Config = ConfigParser.ConfigParser()
		# Options
		opts=[]
		for key in options.keys():
			opts.append('option-'+key)
			Config.add_section('option-'+key)
			for hkey in options[key].keys():
				Config.set('option-'+key, hkey, options[key][hkey])
		# Contacts
		conts=[]
		for key in contacts.keys():
			conts.append('contact-'+key)
			Config.add_section('contact-'+key)
			for hkey in contacts[key].keys():
				Config.set('contact-'+key, hkey, contacts[key][hkey])
		# Notifications
		nots=[]
		for key in notifications.keys():
			nots.append('notification-'+key)
			Config.add_section('notification-'+key)
			for hkey in notifications[key].keys():
				Config.set('notification-'+key, hkey, notifications[key][hkey])

		# Triggers
		trigs=[]
		for key in triggers.keys():
			trigs.append('trigger-'+key)
			Config.add_section('trigger-'+key)
			for hkey in triggers[key].keys():
				Config.set('trigger-'+key, hkey, triggers[key][hkey])
		# Thresholds
		thres=[]
		for key in thresholds.keys():
			thres.append('threshold-'+key)
			Config.add_section('threshold-'+key)
			for hkey in thresholds[key].keys():
				Config.set('threshold-'+key, hkey, thresholds[key][hkey])
		# Sensors
		for key in sensors.keys():
			Config.add_section('sensor-'+key)
			for hkey in sensors[key].keys():
				Config.set('sensor-'+key, hkey, sensors[key][hkey])

		Config.add_section('identifiers')
		Config.set('identifiers', 'options', opts)
		Config.set('identifiers', 'contacts', conts)
		Config.set('identifiers', 'notifications', nots)
		Config.set('identifiers', 'triggers', trigs)
		Config.set('identifiers', 'thresholds', thres)
		Config.write(cfgfile)
		cfgfile.close()

	if not os.path.isfile(configfile_name):
		print "didn't write"
		return(1)
	else:
		print "wrote just fine"
		return(0)

def welcome():
	smith = 1
	while smith:
		try:
			rErr, rMsg = serenaredis.redis_connect()
			if rErr == 0:
				availableUuids = serenaredis.redis_get_available_uuids()
				print 'Final availableUuids: %s'% availableUuids
				if len(availableUuids) >= 1:
					print 'Please select the site'
				else:
					print 'No sites available, please create a new site'
					
			reset()
                except IOError:
                        print "Error"
                except KeyboardInterrupt:
                        reset()
                except SystemExit:
                        reset()
                except:
                        reset()


if __name__ == '__main__':
	# Uncomment the welcome when we go live
	welcome()

