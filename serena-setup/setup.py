import time, grovepi, sys, signal, os, subprocess, ConfigParser
import RPi.GPIO as GPIO
import serenaredis
from grove_rgb_lcd import *
from config_functions import *

selector = 0
button = 2

grovepi.pinMode(selector, "INPUT")
grovepi.pinMode(button, "INPUT")

def sigterm_handler(signum, frame):
        print >> sys.stderr, "Exit received"
        sys.exit(0)


def reset():
	print "Hit reset!"
        setText("Exiting")
        for i in range(0,255):
                setRGB(255-i,0,0)
        setText("")
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

def write_config_old(site_uuid):
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
				if sensors[key][hkey]:
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
			setText("")
			setRGB(100,100,100)
			place = 0
			rErr, rMsg = serenaredis.redis_connect()
			if rErr == 0:
				#for i in range(0,255):
					#setRGB(i,i,i)
					#char_pos_float = i / 6.5
					#char_pos = "%d" %char_pos_float
					#if int(char_pos) > place:
						#setText_norefresh(chr(255)*int(char_pos))
						#place = int(char_pos)
				#dbs = serenaredis.redis_get_serena_databases()
				dbs = serenaredis.redis_get_available_uuids()
                                if len(dbs) >= 1:
					for k, v in dbs.items():
						print(k, v)
						sys.stdout.write('database: [{}] = {}\n'.format(k,v))
			
					# We have m{an}y available UUID that is/are non-active 
					# Let the user select them
					setText("SERENA v0.0.1\nPlease Wait")
					time.sleep(5)
					#setRGB(100,0,100)
					#setText("#1: Use Dial to\nview sites")
					#time.sleep(3)
					#setText("#2: Then Press\nbutton to accept")
					#time.sleep(3)
					#setRGB(0,0,255)
					#db_index,db_name=select_instance(dbs)
					db_index,db_name,site_uuid=select_instance(dbs)
					print "Site selected"
					if len(db_name) > 1:
						print "User selected site: "+db_name
						setRGB(200,80,0)
						setText("Selected Site:\n"+db_name)
						time.sleep(2)
						setText("Writing Conf.\nPlease Wait")
						time.sleep(2)
						#if not write_config(db_index):
						if not write_config_no_update_required(site_uuid):
							setRGB(0,255,0)
							setText("Written Conf\nOK")
							time.sleep(3)
							setText("Rebooting\nPlease Wait")
							from subprocess import call
							call("sudo reboot", shell=True)
							sys.exit(0)
						else:
							setRGB(255,0,0)
							setText("!ERROR Writing!")
							time.sleep(3)
							exit(1)
							
					else:
						setRGB(255,0,0)
						setText("!Unknown site!")
						time.sleep(5)
						exit(1)	
					print "Got Here\n"
					time.sleep(5)
					setText("")
					setRGB(0,0,0)
					smith=0
					exit(0)

                                else:
                                        print 'No sites available, please create a new site'
					setRGB(200,80,0)
					setText("No Sites! Goto serena.local:8088")
					time.sleep(5)
					smith=1
					#exit(0)
					
			else:
				setRGB(255,0,0)
				print "Whoops!"
				setText(rMsg)
				exit(0)
                except IOError:
                        print "Error"
                except KeyboardInterrupt:
                        reset()
                except SystemExit:
                        reset()
                except:
                        setRGB(0,0,0)
                        setText("")


# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	# Uncomment the welcome when we go live
	welcome()

