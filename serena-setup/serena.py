import time, grovepi, sys, signal, os, subprocess, ConfigParser, ast
import RPi.GPIO as GPIO
import serenaredis
from grove_rgb_lcd import *
from ConfigParser import SafeConfigParser

# set color registers
red = 0
green = 0
blue = 0

# set some variables
status = 0
action = 0
options_timeout = 120
green_brightness = 50

# Define globals
config = {}
sensor = {}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def set_sensors():
	global sensor

	if sensor.get('input').get('power'):
		print "Setting input power to port: %s"% sensor['input']['power']
		# Set power detector (GPIO no on grovepi)
		#GPIO.setmode(GPIO.BCM)
		#GPIO.setwarnings(False)
		#GPIO.setup(int(sensor['input']['power']), GPIO.IN, pull_up_down=GPIO.PUD_UP)

	if sensor.get('input').get('dial'):
		print "Setting input dial to port: %s"% sensor['input']['dial']
		grovepi.pinMode(int(sensor['input']['dial']), "INPUT")

	if sensor.get('input').get('button'):
		print "Setting input button to port: %s"% sensor['input']['button']
		grovepi.pinMode(int(sensor['input']['button']), "INPUT")

	if sensor.get('output').get('gLed'):
		print "Setting output gLed to port: %s"% sensor['output']['gLed']
		grovepi.pinMode(int(sensor['output']['gLed']), "OUTPUT")

	if sensor.get('output').get('buzzer'):
		print "Setting output buzzer to port: %s"% sensor['output']['buzzer']
		grovepi.pinMode(int(sensor['output']['buzzer']), "OUTPUT")


def sigterm_handler(signum, frame):
	print >> sys.stderr, "Exit received"
	sys.exit(0)

def reset():
	setText("Exiting")
	for i in range(0,255):
		setRGB(255-i,0,0)
	setText("")
	sys.exit()

def dimScreen():
	for i in range(0,200):
		setRGB(255-i,255-i,255-i)
	global red, green, blue
	red = 50
	green = 50
	blue = 50 

def updateIdle():
	# Might not need this once we start looping through the sensors
	time.sleep(1)
	global status
	global action
	global sensor

	status_indicator = "?"
	power_indicator = "?"

	button = int(sensor['input']['button'])
	#print "got to updateIdle %s"% button
	power = int(sensor['input']['power'])
	#print "\tpower: %s"% power

	#GPIO.setmode(GPIO.BCM)
	#GPIO.setwarnings(False)
	#GPIO.setup(power, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	#grovepi.pinMode(button, "INPUT")

	if int(grovepi.digitalRead(button)):
		action = 1
	if status == 0:
		status_indicator = "-"
		status=1
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 1:
		status_indicator = chr(96)
		status=2
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 2:
		status_indicator = "|"
		status=3
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 3:
		status_indicator = "/"
		status=4
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 4:
		status_indicator = "-"
		status=5
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 5:
		status_indicator = chr(164)
		status=6
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 6:
		status_indicator = "|"
		status=7
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"
	elif status == 7:
		status_indicator = "/"
		status=0
        	if GPIO.input(21):
			power_indicator = "-"
		else:
			power_indicator = "+"

	setText_norefresh("Ready         "
		+power_indicator
		+status_indicator
		+time.strftime("\n%m/%d/%Y %H:%M"))


def goGreen():
	global red, green, blue, green_brightness

	red = 0
	green = green_brightness 
	blue = 0
	setRGB(red,green,blue)

def goRed():
	global red, green, blue
	red = 255
	green = 0
	blue = 0
	setRGB(red,green,blue)

def goBlue():
	global red, green, blue
	red = 0
	green = 0
	blue = 255
	setRGB(red,green,blue)

def goYellow():
	global red, green, blue
	red = 255
	green = 130
	blue = 0
	setRGB(red,green,blue)

def sendSMS(number, message):
	sms_cmd = subprocess.Popen( "sudo gammu-smsd-inject TEXT '"+number+"'", stdin=subprocess.PIPE, shell=True )
	sms_cmd.communicate( message )

def doOptions():
	global action, green_brightness, sensor
	goBlue()
	for i in range(0,120):
		s_value = grovepi.analogRead(int(sensor['input']['dial']))
		b = (s_value / 4) / 10
		left = 120-i
		left = "%03d" %left
		if int(b) <= 6:
			setText_norefresh("Option 1/5: |"+str(left)+" "+chr(126)+" Shutdown!          ");
			if int(grovepi.digitalRead(int(sensor['input']['button']))):
				goYellow()
				print "Powering off"
				setText("Powering Off")
				time.sleep(2)
				goRed()
				setText("Remove power after green LED activity")
				time.sleep(3)
				setText("")
				setRGB(0,0,0)
				from subprocess import call
				call("sudo poweroff", shell=True)
		elif int(b) >= 7 and int(b) <= 12:
			setText_norefresh("Option 2/5: |"+str(left)+" "+chr(126)+" Reboot!            ");
			if int(grovepi.digitalRead(int(sensor['input']['button']))):
				print "Rebooting"
				setText("Rebooting\nPlease Wait")
				from subprocess import call
				call("sudo reboot", shell=True)
		elif int(b) >= 13 and int(b) <= 18:
			setText_norefresh("Option 3/5: |"+str(left)+" "+chr(126)+" Set gBrightness    ");
			if int(grovepi.digitalRead(int(sensor['input']['button']))):
				setText("Rotate dial to  desired level")
				time.sleep(2)
				for gb in range (0,20):
					s_value = grovepi.analogRead(int(sensor['input']['dial']))
					green_brightness = s_value / 4
					goGreen()
					tleft = 20-gb
					tleft = "%02d" %tleft
					setText_norefresh("Time Left:   "+str(tleft)+"  GreenLevel: "+str(green_brightness)+"  ");
					time.sleep(.5)
				setText("Green Level set")
				time.sleep(1)
		elif int(b) >= 19 and int(b) <= 24:
			setText_norefresh("Option 4/5: |"+str(left)+" "+chr(126)+" Test SMS           ");
			if int(grovepi.digitalRead(int(sensor['input']['button']))):
				setText("Sending Test SMS")
				time.sleep(2)
				send_startup_sms('SERENA is checking in')
				time.sleep(5)
				setText_norefresh("Sending Test SMSSENT")
				time.sleep(2)
		elif int(b) >= 25:
			setText_norefresh("Option 5/5: |"+str(left)+" "+chr(126)+" Exit Options       ");
			if int(grovepi.digitalRead(int(sensor['input']['button']))):
				setText("Exiting Options")
				time.sleep(2)
				break

		#print("selector value: %d and b %d" % (s_value,b))
	setText("")
	dimScreen()
	goGreen()
	action = 0

def send_startup_sms(override_message="SERENA Started Up"):
	global config
	if config.has_option('option-startup', 'sms'):
		if config.get('option-startup','sms'):
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
							sendSMS(cid_sms, sms_message)

def welcome():
	global config, sensor
	smith = 1
	while smith:
		try:
			setText("")
			place = 0
			serenaredis.redis_connect()
			serenaredis.redis_set_powerOn()
			serenaredis.redis_set_timeStamp()
			for i in range(0,255):
				setRGB(i,i,i)
				char_pos_float = i / 6.5
				char_pos = "%d" %char_pos_float
				if int(char_pos) > place:
					setText_norefresh(chr(255)*int(char_pos))
					place = int(char_pos)
			setText("SERENA v0.0.1\n[TRB]")
			#sendSMS('+18082341234', 'Hello Ian, SERENA started up.')
			#time.sleep(5)
			# load configuration
			setText("Loading Config\nPlease Wait")
			try:
				config = SafeConfigParser()
				config.read('config.yaml')
				#for section_name in config.sections():
				if config.has_section('option-startup'):
					send_startup_sms()

				siteInitials = config.get('option-court','initials');
				if siteInitials:
					# Update Site Counters
					serenaredis.redis_set_powerOn(siteInitials)
					serenaredis.redis_set_timeStamp(siteInitials)

				# We're setting the sensor global so other functions can access it
				if config.has_section('sensor-input'):
					sensor['input'] = {}
					for key, val in config.items('sensor-input'):
						print "key: %s = %s"% (key,val)
						sensor['input'][key] = val
				if config.has_section('sensor-output'):
					sensor['output'] = {}
					for key, val in config.items('sensor-output'):
						print "key: %s = %s"% (key,val)
						sensor['output'][key] = val
				set_sensors()

			except ConfigParser.ParsingError, err:
				setRGB(255,0,0)
				print 'Could not parse:', err
				setText("Error reading\nConf file")
				time.sleep(5)
			setText("")
			dimScreen()
			goGreen()
			smith=0
		except KeyboardInterrupt:
			reset()


# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

def doLoop():
	while True:
		try:
			if action == 0:
				goGreen()
				updateIdle()
			if action == 1:
				doOptions()
			else:
				#for section_name in config.sections():
					#print "section: %s"% section_name
				updateIdle()

		except IOError:
			print "Error"
		except KeyboardInterrupt:
			reset()
		except SystemExit:
			reset()
		except:
			setRGB(0,0,0)
			setText("")


if __name__ == '__main__':
	# Uncomment the welcome when we go live
	conf=welcome()
	doLoop()
