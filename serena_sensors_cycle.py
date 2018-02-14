#!/usr/bin/python

import argparse,socket,redis,time,math,ConfigParser,sys,signal,os,ast,subprocess,grovepi,grove_rgb_lcd
import RPi.GPIO as GPIO
from ConfigParser import SafeConfigParser
from rq import Queue
from rq_def_modules import sendSMS
from grovepi import *
from grove_rgb_lcd import *

# Define Globals
r_server = {}
host = ""
port = ""
auth = ""
database = ""
sock = {}
result={}
config = {}
io = {}
q = {}
execution = {}
execution_history = []
alert = {'lcd_message': '', 'acknowledged': ''}
status_indicators = [ '-', chr(96), '|', '/', '-', chr(164), '|', '/' ]
manual_override_timeout = 60
manual_override_lifespan = 600
flip_flop = 0
current_status = 0
start_motion_epoch = 0
redis_sensor_path = ''

# Redis Parent globals
r_server_parent = {}
sock_parent = {}
result_parent = {}

# define colors for LCD Background
lcd_background_color = {
	'red': {'red': 255, 'green': 0, 'blue': 0},
	'green': {'red': 0, 'green':255, 'blue': 0},
	'blue': {'red': 0, 'green': 0, 'blue': 255},
	'white': {'red': 255, 'green': 255, 'blue': 255},
	'yellow': {'red': 255, 'green': 130, 'blue': 0},
	'purple': {'red': 128, 'green': 0, 'blue': 128}}

# set some variables
cycle = 0
options_timeout = 120
green_brightness = 50


def reset(allDone=0):
	global io
	print 'hit reset'
	reset_redis_alerts()
        setText("Exiting")
        for i in range(0,255):
                setRGB(255-i,0,0)
	grovepi.digitalWrite(int(io['output']['gled']),0)
	trigger_alarm_outputs(0)
        setText("")
	if allDone:
	        sys.exit()


def determine_lcd_status_text_based_from_inputs(input):
	global status_indicators,cycle
	status_indicator = status_indicators[cycle]

	if 'water' in input:
		if input['water']:
			water_indicator = "-"
		else:
			water_indicator = "+"
	else:
		water_indicator = "?"

	if 'power' in input:
		if input['power']:
			power_indicator = "-"
		else:
			power_indicator = "+"
	else:
		power_indicator = "?"

	if 'motion' in input:
		if input['motion']:
			motion_indicator = "-"
			#print 'Motion Detected'
			#send_motion_capture_request()
			# June 9th 2017 Moving motion capture to the Threshold checker
		else:
			motion_indicator = "+"
	else:
		motion_indicator = "?"

	temp = "??"
	if not math.isnan(input['temperatureC']):
		if int(input['temperatureC']) > 0 and int(input['temperatureC']) < 100:
			temp = str(int(input['temperatureF']))
	hum = "??"
	if not math.isnan(input['humidity']):
		if int(input['humidity']) > 0 and int(input['humidity']) < 100:
			hum = str(int(input['humidity']))

	msg = str(status_indicator
		+" T"+temp
		+" H"+hum
		+" P"+power_indicator
		+" W"+water_indicator
		+" "+time.strftime("\n%m%d%y %H:%M")
		+" M"+motion_indicator)

	return msg


def update_screen_color():
	global current_status

	if current_status == 0:
		# Normal operations
		set_lcd_background_color('green')
	elif current_status == 1:
		# Early warning detected
		set_lcd_background_color('yellow')
	elif current_status == 2:
		# Alert condition meet (threshold breached)
		set_lcd_background_color('red')
	elif current_status == 3:
		# Alert Acknowledged (Somebody responded to alert)
		set_lcd_background_color('purple')
	elif current_status == 4:
		# Muted Early Warning 
		set_lcd_background_color('white')


def determine_early_warning(input):
	
	# Only applicable to Power loss and Water detection
	early_warning = {'sensors':[]}
	if 'water' in input:
		if input['water']:
			early_warning['sensors'].append('water');
	if 'power' in input:
		if input['power']:
			early_warning['sensors'].append('power');
	# Work out how to get early warnings for temp and humidity

	# Temperature and Humidity will be taken care of by the Threshold cycle
	# since that process can compare epochs and determine if we have stale
	# values and thus an alert condition, then trigger an alert
	# We're using the DHT11 and that can only capture 0 - 50 degree Celsius
	# Humidity: 20% - 80/90% Relative humdity (80% at higher temps and 90% at lower temps)
	#temp = "??"
	#if not math.isnan(input['temperatureC']):
	#	if int(input['temperatureC']) > 0 and int(input['temperatureC']) < 500:
	#		temp = str(int(input['temperatureF']))
	#hum = "??"
	#if not math.isnan(input['humidity']):
	#	if int(input['humidity']) > 0 and int(input['humidity']) < 100:
	#		hum = str(int(input['humidity']))
	return early_warning


def check_current_status(input):
	global current_status

	# REDIS alarms take priority over early warnings

	#print "\t[CCS]"
	early = determine_early_warning(input)
	redis_status = get_redis_alert_status()

	if redis_status['lcd_message']:
 		if redis_status['acknowledged']:
			# Acknowledged Alarm
			current_status = 3
		else:
			# Alarm active and unanwsered
			current_status = 2
	else:
 		if redis_status['acknowledged']:
			if not early['sensors']:
				current_status = 0
			else:
				# Muted Early Warning (no active alarm)
				current_status = 4
		else:
			if early['sensors']:
				# Early Warning
				current_status = 1
			else:
				# OK
				current_status = 0

	print '\t\t[CCS] CURRENT STATUS = [%s] | Redis: %s'% (current_status,redis_status)
	return redis_status,early['sensors']


def promote_early_warning(sensors="unknown"):
	global r_server
	# If a user name isn't passed then we use epoch
	# an epoch value represents an acknowledged action directly from Serena
	# or rather somebody pushed the button!
	#print 'pew'
	delete_redis_acknowledged()
	r_server.hset('alerts:serena', 'lcd_message', sensors)


def delete_redis_acknowledged():
	global r_server
	#print 'dra'
	r_server.delete('alerts:serena', 'acknowledged')


def get_redis_alert_status():
	global r_server
	#print 'gras'
	message_for_lcd = r_server.hget('alerts:serena', 'lcd_message')
	acknowledged = r_server.hget('alerts:serena', 'acknowledged')
	return {'lcd_message': message_for_lcd,
		'acknowledged': acknowledged}


def check_redis_status():
	global current_status

	redis_status = get_redis_alert_status()
	if redis_status['lcd_message']:
 		if redis_status['acknowledged']:
			# Acknowledged Alarm
			current_status = 3
		else:
			# Alarm active and unanwsered
			current_status = 2
	else:
 		if redis_status['acknowledged']:
			# Muted Early Warning (no active alarm)
			current_status = 4
		else:
			current_status = 0
	print '\t\t[CRS] CURRENT STATUS = [%s] | Redis: %s'% (current_status,redis_status)
	return redis_status


def reset_redis_alerts():
	global r_server
	pipe = r_server.pipeline()
	pipe.hset('alerts:serena', 'manually_overridden', '')
	pipe.hset('alerts:serena', 'lcd_message', '')
	pipe.hset('alerts:serena', 'acknowledged', '')
	pipe.hset('alerts:serena', 'last_acknowledgment', '')
	pipe.execute()


def update_last_ack(time_to_display=999):
	# Either set or delete last_ack of alert
	# We're doing this so the lcd screen can show the last alert for a specific number of seconds
	# afterwhich we'll clear the last alert message so the lcd screen can resume
	global r_server
	value = r_server.hget('alerts:serena', 'last_acknowledgment')
	if value:
		if int(time.time()) > (int(value)+time_to_display):
			print "Resetting Serena"
			# if time now is greater than the last acknowledged alarm + 10 minutes say
			# Clear redis flags. This will basically reset serena
			reset_redis_alerts()
			return 0
		else:
			timeleft = (int(value)+time_to_display)-int(time.time())
			print 'Still %s seconds to go before I reset serena!'% timeleft
			return timeleft
	else:
		print 'Setting last_acknowledgment epoch'
		r_server.hset('alerts:serena', 'last_acknowledgment', int(time.time()))
		return 0


def set_manual_override():
	global r_server
	#print "smo"
	r_server.hset('alerts:serena', 'manually_overridden', int(time.time()))
	r_server.hset('alerts:serena', 'acknowledged', int(time.time()))


def get_manual_override():
	global r_server
	#print "gmo"
	value = r_server.hget('alerts:serena', 'manually_overridden')
	if value:
		return int(value)
	else:
		return 0

def delete_manual_override():
	global r_server
	#print "dmo"
	r_server.delete('alerts:serena','manually_overridden')
	delete_redis_acknowledged()


def trigger_alarm_outputs(status):
	global io
	if 'buzzer' in io['output']:
		grovepi.digitalWrite(int(io['output']['buzzer']),int(status))
	if 'rled' in io['output']:
		grovepi.digitalWrite(int(io['output']['rled']),int(status))

	
def update_idle(input):
	global cycle,alert,io,manual_override_timeout,manual_override_lifespan,timeout,flip_flop,current_status

	# reset alartm outputs
	trigger_alarm_outputs(0)

	# output the input status
	#print "\t\tinput: %s"% input

	# Should we engueue a job here to look for problems in the REDIS data?
	# The job would look for thresholds that have been surpassed and set a REDIS variable
	# that we pickup here and display the status on every other screen.
	# We could use the odd vs even principle on the cycle value to determine
	# if we show the current status vs alert status

	if current_status == 0:
		manual_override_timeout = 60

   	# even cycles will always show sensor status text
	if (cycle % 2 == 0):
		setText_norefresh(determine_lcd_status_text_based_from_inputs(input))
		update_screen_color()
	else: #odd - display REDIS alert conditions
		# Check for alerts captured in REDIS
		# A queued job will update REDIS with the status to display
		# The same queued job will also perform the notifications
		# and escalations of problems

		# Look for redis status (will update current_status)
		redis_status,early_warning_sensors = check_current_status(input)
		update_screen_color()

		if current_status == 1: # Early Warning
			if input['button']:
				setText_norefresh("ABORTING ALERT! Please wait...      ")
				set_manual_override()
				print "MANUALLY OVERRIDDING THE EARLY WARNING FOR THE NEXT 5 MINUTES!!!"
				time.sleep(3)
			else:
       				for i in range(0,5):
					trigger_alarm_outputs(1)
					time.sleep(0.1)
					trigger_alarm_outputs(0)
					time.sleep(0.1)
				if flip_flop == 1:
					setText_norefresh("WILL SEND ALERT IN "+str(manual_override_timeout)+" CYCLES    ")
					time.sleep(2)
					flip_flop=0
       				
				else:
					setText_norefresh("HOLD DOWN BUTTON TO ABORT ALERT    ")
					time.sleep(2)
					flip_flop=1
				manual_override_timeout=manual_override_timeout-2
				if manual_override_timeout < 0:
					print "\t\t!!! PROMOTING EARLY WARNING !!!"
					# Promote early warning to Active Alarm!
					promote_early_warning(early_warning_sensors)
					# Reset manual_override_timeout value
					manual_override_timeout = 60
		elif current_status == 2: # Alarm Active and Unanswered
			# Button can be used to silence
			# also a SMS response can also be used
			if input['button']:
				setText_norefresh("ABORTING ALARM! Please wait...      ")
				print "CANCELLING THE ALARM !!!"
				time.sleep(3)
				reset_redis_alerts()
			else:
				if flip_flop == 1:
					setText("ALERT:\n"+redis_status['lcd_message'])
					trigger_alarm_outputs(1)
					flip_flop=0
				else:
					setText_norefresh("HOLD DOWN BUTTON TO ABORT ALERT    ")
					flip_flop=1
					trigger_alarm_outputs(1)
		elif current_status == 3: # Aknowledged Alarm State and Responding
			print 'Acknowledged, updating last_ack'
			timeleft = update_last_ack(800)
			setText("ACK: "+redis_status['lcd_message']+"\n["+str(timeleft)+"] by "+redis_status['acknowledged']+"        ")
		elif current_status == 4: # Muted Early Warning (no active alarm)
			# Manually overridden early warning
			print 'REDIS STATUS: %s'% redis_status
			starting_epoch = int(redis_status['acknowledged'])
			ack_epoch_ends = starting_epoch+600
			print 'starting_epoch: %s, ack_epoch_ends: %s, now: %s'% (starting_epoch,ack_epoch_ends,int(time.time()))
			if ack_epoch_ends < int(time.time()):
				# acknowledged early warning has expired
				print '\t\t\tDELETING MANUAL OVERRIDE !!!'
				delete_manual_override()
			else:
				timeleft = ack_epoch_ends-int(time.time())
				print "TIMELEFT: %s"% timeleft
				setText_norefresh("ALERT OVERRIDDEN"+str(timeleft)+" seconds left    ")
				
		else: # Everything looks fine
			if redis_status['acknowledged'] and not redis_status['lcd_message']:
				delete_manual_override()
			if input['button']:
				doOptions()
			else:
				setText_norefresh(determine_lcd_status_text_based_from_inputs(input))

	if cycle < 7:
		print "\n--[ Cycle: %s"% cycle
		cycle=cycle+1
	else:
		cycle=0
		set_active_uuid()


	
def set_active_uuid():
	global r_server, r_server_parent, result_parent, config
	#print "sau"
	site_uuid = config.get('options-siteInfo','site_uuid')
	app_uuid = config.get('options-siteInfo','app_uuid')
	hostname = config.get('options-siteInfo','hostname')
	parent_hostname = config.get('options-siteInfo','parenthostname')
	
	if site_uuid:
		if app_uuid:
			if hostname == parent_hostname:
				r_server.hmset('active_uuids:'+site_uuid, {'epoch': int(time.time()),
					'app_uuid':str(app_uuid),'hostname':socket.gethostname(),
					'ip':get_ip()})
				# expire this active uuid in 30 seconds
				r_server.expire('active_uuids:'+site_uuid, 30)
			else:
				if result_parent == 0:
					print 'Saving to r_server_parent'
					r_server_parent.hmset('active_uuids:'+site_uuid, {'epoch': int(time.time()),
						'app_uuid':str(app_uuid),'hostname':socket.gethostname(),
						'ip':get_ip()})
					# expire this active uuid in 30 seconds
					r_server_parent.expire('active_uuids:'+site_uuid, 30)
				else:
					print 'Problem with remote parent connection [%s], retrying connection.'% result_parent 
					connect_to_redis_parent()
	

def set_lcd_background_color(color='green'):
	global lcd_background_color
	setRGB(lcd_background_color[color]['red'],lcd_background_color[color]['green'],lcd_background_color[color]['blue'])


def send_startup_sms(override_message="SERENA Started Up"):
	global config, q
	if config.has_section('notification-serenaStart'):
		if config.has_option('notification-serenaStart','contacts'):
			cid = ast.literal_eval(config.get('notification-serenaStart','contacts'))
			for contact_id in cid:
				contact_section_id = 'contact-%s'% contact_id
			if config.has_option(contact_section_id,'textnumber'):
				cid_sms = config.get(contact_section_id,'textnumber')
				print "Sending Startup SMS to %s"% cid_sms
				sms_message = "Hello %s, "% config.get(contact_section_id,'name')
				sms_message += override_message
				#job = q.enqueue(sendSMS, cid_sms, sms_message)
				# Set ttl to 180 seconds so we don't maintain jobs if worker isn't awake
				job = q.enqueue_call(func=sendSMS,
					args=(cid_sms, sms_message),
					timeout=60,
					ttl=180,
					at_front=1)


def load_configuration():
	global io, config, q, redis_sensor_path
	try:
		config = SafeConfigParser()
		config.read('config.yaml')

		if config.get('options-startup','sms'):
			send_startup_sms()

		siteInitials = config.get('options-siteInfo','courtinitials')
		if siteInitials:
			# Update Site Counters
			print "siteInitials: %s"% siteInitials
			#serenaredis.redis_set_powerOn(siteInitials)
			#serenaredis.redis_set_timeStamp(siteInitials)

		if config.has_section('options-redis'):
			if config.get('options-redis', 'sensor_path'):
				#redis_sensor_path = config.get('options-redis', 'sensor_path') + ":" + siteInitials + ":"
				redis_sensor_path = config.get('options-redis', 'sensor_path') + ":"
			else:
				redis_sensor_path = "unknown:"

		# We're setting the io global so other functions can access it
		if config.has_section('sensors-input'):
			io['input'] = {}
			for key, val in config.items('sensors-input'):
				print "key: %s = %s"% (key,val)
				io['input'][key] = val
		if config.has_section('sensors-output'):
			io['output'] = {}
			for key, val in config.items('sensors-output'):
				print "key: %s = %s"% (key,val)
				io['output'][key] = val
		set_io_ports()
		# What does io look like at this point?
		print "\t\tio: %s"% io
	except ConfigParser.ParsingError, err:
		print 'Could not parse:', err


def set_io_ports():
	global io

	for stype in io:
		for sname in io[stype]:
			if stype == "input" and sname == "power":
               			GPIO.setmode(GPIO.BCM)
		                GPIO.setwarnings(False)
		                GPIO.setup(int(io[stype][sname]), GPIO.IN, pull_up_down=GPIO.PUD_UP)
			else:
				print '[%s] Setup: %s on port %s'% (stype, sname, int(io[stype][sname]))
               			grovepi.pinMode(int(io[stype][sname]), stype)


def get_args():
	global host,port,auth,database

	# Assign description to the help doc
	parser = argparse.ArgumentParser(
			description='Serena Core input cycler.')
	# Add arguments
	parser.add_argument(
			'-H', '--host', type=str, help='Host name or IP', required=True)
	parser.add_argument(
			'-P', '--port', type=int, help='Port number', required=True)
	parser.add_argument(
			'-A', '--auth', type=str, help='Auth password', required=False, default=None)
	parser.add_argument(
			'-D', '--database', type=int, help='Database number', required=False)
	# Array for all arguments passed to script
	args = parser.parse_args()
	# Assign args to variables
	host = args.host
	port = args.port
	auth = args.auth
	#return host, port, auth, database
	# Nothig to return since we switched to globals


def check_dht():
	global io
	#print 'check_dht'

	# There are two types of DHT sensor, a blue one (generic, not ver good)
	# and a more accurate white sensor
	# I haven't worked out a method of capturing the color in the configuration
	# just yet, so I'm hardcoding it here. TODO
	# Blue sensor (2nd param is 0)
        #[ temp,hume ] = grovepi.dht(int(io['input']['dht']),0)
	# White sensor (2nd param is 1)
	#print 'dht sensor is on port: %s'% int(io['input']['dht'])
        [ temp,hume ] = grovepi.dht(int(io['input']['dht']),1)
	time.sleep(1)
        [ temp,hume ] = grovepi.dht(int(io['input']['dht']),1)
	time.sleep(1)
        #[ temp,hume ] = grovepi.dht(8,1)
	#print 'temp: %s, hume: %s'% (temp,hume)
        t = str(temp)
	#print 't: %s'% t
        h = str(hume)
	#print 'h: %s'% h
        t.rstrip("0")
        h.rstrip("0")
        s = "T:"+t+"C H:"+h+"%"
        #print "\t\tReporting: %s"% s
	return (t,h)


def check_button():
	global io
	# A return value of 1 indicates the button is pressed
	if grovepi.digitalRead(int(io['input']['button'])):
		return 1
	else:
		return 0

def check_water():
	global io
	# A return value of 1 indicates water was detected
	if grovepi.digitalRead(int(io['input']['water'])):
		return 0
	else:
		return 1


def check_power():
	global io
	# A return value of 1 indicates a loss of power
	if GPIO.input(int(io['input']['power'])):
		return 1
	else:
		return 0


def check_motion():
	global io
	# A return value of 1 indicates motion was detected
	if grovepi.digitalRead(int(io['input']['pir'])):
		return 1
	else:
		return 0


def connect_to_redis_parent():
	global sock_parent,result_parent,r_server_parent

	# Connect to Parent REDIS (serena.local) Used for multi sites
	# Serena Sensors Cycles needs to update the active_uuids redis key
	r_server_parent = redis.Redis('serena.local', 6379)
	sock_parent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result_parent = sock_parent.connect_ex(('127.0.0.1', 6379))
	# A result_parent value of zero means no errors were encountered with the connection
	print 'result_parent returned: %s'% result_parent


def connect_to_redis():
	global host,port,auth,database,sock,result,r_server,q

	# Connect to REDIS
	r_server = redis.Redis(host=host,
				port=port,
				password=auth,
				db=database)
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect_ex((host, port))
	# A result value of zero means no errors were encountered with the connection
	# Tell RQ which Redis connection to use
	q = Queue(connection=r_server)  # no args implies the default queue


def start_up():
	global io,cofig

	grovepi.digitalWrite(int(io['output']['gled']),1)
	setText("")
	place = 0
	for i in range(0,255):
		setRGB(i,i,i)
		char_pos_float = i / 6.5
		char_pos = "%d" %char_pos_float
		if int(char_pos) > place:
			setText_norefresh(chr(255)*int(char_pos))
			place = int(char_pos)
	siteInitials = config.get('options-siteInfo','courtinitials')
	setText("SERENA v0.0.1\n["+siteInitials+"]")
	time.sleep(2)

def check_serena_hotness():
	p = subprocess.Popen(['cat', '/sys/class/thermal/thermal_zone0/temp'], stdout=subprocess.PIPE)
	cpuTemp = float(p.communicate()[0].rstrip())/1000
	cleanCpuTemp = float("{0:.1f}".format(cpuTemp))
	if not math.isnan(cpuTemp):
		if int(cpuTemp) > 0 and int(cpuTemp) < 100:
			#print 'returning cpu Temp of: >%.1f<'% cpuTemp
			return cleanCpuTemp
		else:
			return 0
	else:
		return 0
	
def cycle_sensors():
	global r_server, execution, redis_sensor_path, config
	#print 'cycle_sensors:%s'% int(time.time())
	#print 'redis_sensor_path: %s'% redis_sensor_path

	execution['input'] = {'start': time.time(), 'end': time.time()}

	# create sensor dictionary and set epoch
	sensors = {'epoch': int(time.time())}

	# Temperature and Humidty capture - everything becomes a float!
	sensorTemp, sensorHum = check_dht()
	#sensorTemp = 80
	#sensorHum = 35
	sensors['serenaTemp'] = check_serena_hotness()
	sensors['temperature'] = float(sensorTemp)
	sensors['temperatureC'] = float(sensorTemp)
	sensors['temperatureF'] = (float(sensorTemp) * 9.0 / 5.0) + 32
	sensors['humidity'] = float(sensorHum)

	# Power status capture
	#sensors['power'] = check_power()

	# Water detection capture
	if config.has_option('sensors-input','water'):
		sensors['water'] = check_water()
	# skip since I haven't connected the rj11 cable yet! June 23rd 2017
	#sensors['water'] = 0

	# button detection capture
	sensors['button'] = check_button()

	# Motion / PIR detection capture
	if config.has_option('sensors-input','pir'):
		sensors['motion'] = check_motion()

	# Power status capture
	if config.has_option('sensors-input','power'):
		sensors['power'] = check_power()

	# What is our sensors dictionary looking like?
	print "\t\tsensors: %s"% sensors

	pipe = r_server.pipeline()

	# NEED TO COME BACK AROUND TO THIS FOR THE SENSOR MAPPINGS
	# ALSO NEED TO SORT OUT THE temperatureC and temperatureF
	# SINCE temperatureC is being captured as temperature below

	# This redis library has flipped score and value around!
	# Watch out for this bug if we ever update the redis library (since it was fixed later!)
	#
	# Serena's CPU temperature
	if not math.isnan(sensors['serenaTemp']):
		if int(sensors['serenaTemp']) > 0 and int(sensors['serenaTemp']) < 100:
			pipe.zadd(redis_sensor_path+'serenaTemp',
				str(sensors['epoch'])+":"+str(sensors['serenaTemp']),
				sensors['epoch'])

	# DHT Temperature
	if not math.isnan(sensors['temperatureC']):
		if int(sensors['temperatureC']) > 0 and int(sensors['temperatureC']) < 100:
			pipe.zadd(redis_sensor_path+'temperature',
				str(sensors['epoch'])+":"+str(sensors['temperature']),
				sensors['epoch'])
			#pipe.zadd(redis_sensor_path+'temperatureF',
				#str(sensors['epoch'])+":"+str(sensors['temperatureF']),
				#sensors['epoch'])
	# DHT Humidity
	if not math.isnan(sensors['humidity']):
		if int(sensors['humidity']) > 0 and int(sensors['humidity']) < 100:
			pipe.zadd(redis_sensor_path+'humidity',
				str(sensors['epoch'])+":"+str(sensors['humidity']),
				sensors['epoch'])
	# Power
	if config.has_option('sensors-input','power'):
		pipe.zadd(redis_sensor_path+'power',
			str(sensors['epoch'])+":"+str(sensors['power']),
			sensors['epoch'])
	# Water
	if config.has_option('sensors-input','water'):
		pipe.zadd(redis_sensor_path+'water',
			str(sensors['epoch'])+":"+str(sensors['water']),
			sensors['epoch'])
	# Motion
	if config.has_option('sensors-input','pir'):
		pipe.zadd(redis_sensor_path+'motion',
			str(sensors['epoch'])+":"+str(sensors['motion']),
			sensors['epoch'])
	# Button
	pipe.zadd(redis_sensor_path+'button',
		str(sensors['epoch'])+":"+str(sensors['button']),
		sensors['epoch'])
	# Execute
	pipe.execute()

	execution['input']['end'] = time.time()
	execution['output'] = {'start': time.time(), 'end': time.time()}

	# Since we cannot have multiple python program interfacing with the GrovePi libs
	# we must handle all input and output in the cycle_sensors loop

	# sleep until 5 seconds has expired
	# We should probably measure how long it takes to go through the sensors and 
	# also how long it takes to go through the output updates to know the time
	# value of how long it takes for input checking and output updating
	# and adjust a wait period accordingly. For right now we'll use 5 seconds
	#
	# This is just a temporary work around at the moment.
	#
	while (sensors['epoch']+1 > int(time.time())):
		#print "%s > %s?"% (sensors['epoch']+5, int(time.time()))
		time.sleep(0.1)

	# Now to setup what we want to output
	update_idle(sensors)

	execution['output']['end'] = time.time()
	input_time = execution['input']['end']-execution['input']['start']
	output_time = execution['output']['end']-execution['output']['start']
	# Skipping the following since we don't want to take these measurements yet
	#capture_execution(input_time,output_time)
	print "\t\texecution: [Input:%.2f] [Output:%.2f]"% (input_time,output_time)

def capture_execution(itime,otime):
	# Nothing to do yet
	# But I'd like to sample the last 10 executions / cycles and see if we 
	# can find out a mean execution time to use maybe?
	return true


def reset_grovepi():
        from subprocess import call
        call("avrdude -c gpio -p m328p", shell=True)


def doOptions():
	global io
	set_lcd_background_color('blue')
	setText("Please release  the button!")
	time.sleep(3)
	for i in range(0,120):
                # The next try statement is to address a kernel bug in 4.9.5 - Aug 2017
                try:
                        s_value = grovepi.analogRead(int(io['input']['dial']))
                except:
                        print 'Need to reset the Grovepi, must have the kernel bug!'
                        reset_grovepi()
		s_value = grovepi.analogRead(int(io['input']['dial']))
		b = (s_value / 4) / 10
		left = 120-i
		left = "%03d" %left
		if int(b) <= 6:
			setText_norefresh("Option 1/5: |"+str(left)+" "+chr(126)+" Shutdown!          ");
			if int(grovepi.digitalRead(int(io['input']['button']))):
				set_lcd_background_color('yellow')
				print "Powering off"
				setText("Powering Off")
				time.sleep(2)
				set_lcd_background_color('red')
				setText("Remove power after green LED activity")
				time.sleep(3)
				setText("")
				setRGB(0,0,0)
				from subprocess import call
				call("sudo poweroff", shell=True)
		elif int(b) >= 7 and int(b) <= 12:
			setText_norefresh("Option 2/5: |"+str(left)+" "+chr(126)+" Reboot!            ");
			if int(grovepi.digitalRead(int(io['input']['button']))):
				print "Rebooting"
				setText("Rebooting\nPlease Wait")
				from subprocess import call
				call("sudo reboot", shell=True)
		elif int(b) >= 13 and int(b) <= 18:
			setText_norefresh("Option 3/5: |"+str(left)+" "+chr(126)+" Set gBrightness    ");
			if int(grovepi.digitalRead(int(io['input']['button']))):
				setText("Rotate dial to  desired level")
				time.sleep(2)
				for gb in range (0,20):
					s_value = grovepi.analogRead(int(io['input']['dial']))
					#green_brightness = s_value / 4
					set_lcd_background_color('green')
					tleft = 20-gb
					tleft = "%02d" %tleft
					setText_norefresh("Time Left:   "+str(tleft)+"  GreenLevel: ??       ");
					time.sleep(.5)
				setText("Green Level set")
				time.sleep(1)
		elif int(b) >= 19 and int(b) <= 24:
			setText_norefresh("Option 4/5: |"+str(left)+" "+chr(126)+" Test SMS           ");
			if int(grovepi.digitalRead(int(io['input']['button']))):
				setText("Skipping!   NOT Sending Test SMS")
				time.sleep(2)
				#send_startup_sms('SERENA is checking in')
				#time.sleep(5)
				#setText_norefresh("Sending Test SMSSENT")
				time.sleep(2)
		elif int(b) >= 25:
			setText_norefresh("Option 5/5: |"+str(left)+" "+chr(126)+" Exit Options       ");
			if int(grovepi.digitalRead(int(io['input']['button']))):
				setText("Exiting Options")
				time.sleep(2)
				break
	setText("")


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def doLoop():
	while True:
		try:
			cycle_sensors()
		except IOError:
			print "Error"
		except KeyboardInterrupt:
			print "Exit requested"
			reset(1)
		except SystemExit:
			print "System Exit requested"
			reset(1)
		except TypeError:
			print "Type Error!"

def sigterm_handler(signum, frame):
        print >> sys.stderr, "Exit received"
        setText("Exiting")
        for i in range(0,255):
                setRGB(255-i,0,0)
        trigger_alarm_outputs(0)
        setText("")
	reset(1)
        sys.exit(0)

# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGINT, sigterm_handler)
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	get_args()
	connect_to_redis()
	load_configuration()
	start_up()
	doLoop()
