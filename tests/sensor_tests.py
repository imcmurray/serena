#!/usr/bin/python

import time,math,sys,signal,os,ast,subprocess,grovepi
import RPi.GPIO as GPIO
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
io = {'input': {'dial': '0', 'pir': '3', 'button': '2', 'dht': '4', 'power': '21', 'water': '8' }, 'output': {'buzzer': '7', 'rled': '6', 'gled': '5'}}
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

# set some variables
cycle = 0
options_timeout = 120
green_brightness = 50


def reset():
	trigger_outputs(0)
        sys.exit()


def set_io_ports():
	global io

	for stype in io:
		for sname in io[stype]:
			if stype == "input" and sname == "power":
               			#GPIO.setmode(GPIO.BOARD)
               			GPIO.setmode(GPIO.BCM)
		                GPIO.setwarnings(False)
		                GPIO.setup(int(io[stype][sname]), GPIO.IN, pull_up_down=GPIO.PUD_UP)
			else:
				print '[%s] Setup: %s on port %s'% (stype, sname, int(io[stype][sname]))
               			grovepi.pinMode(int(io[stype][sname]), stype)



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
	time.sleep(.5)
        [ temp,hume ] = grovepi.dht(int(io['input']['dht']),1)
	time.sleep(.5)
        t = str(temp)
	#print 't: %s'% t
        h = str(hume)
	#print 'h: %s'% h
        t.rstrip("0")
        h.rstrip("0")
        #s = "T:"+t+"C H:"+h+"%"
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
	#if GPIO.input(int(io['input']['power'])):
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


def check_dial():
	global io
	# A return value of 1 indicates motion was detected
	return int(grovepi.analogRead(int(io['input']['dial'])))



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

def trigger_outputs(status):
	global io
	grovepi.digitalWrite(int(io['output']['buzzer']),int(status))
	grovepi.digitalWrite(int(io['output']['rled']),int(status))
	grovepi.digitalWrite(int(io['output']['gled']),int(status))
	
def cycle_sensors():
	global r_server, execution, redis_sensor_path

	# create sensor dictionary and set epoch
	sensors = {'epoch': int(time.time())}

	# Temperature and Humidty capture - everything becomes a float!
	sensors['serenaTemp'] = check_serena_hotness()
	if 'dht' in io['input']:
		sensorTemp, sensorHum = check_dht()
		#sensors['temperature'] = float(sensorTemp)
		sensors['temperatureC'] = float(sensorTemp)
		sensors['temperatureF'] = float("{0:.2f}".format((float(sensorTemp) * 9.0 / 5.0) + 32))
		sensors['humidity'] = float(sensorHum)

	if 'power' in io['input']:
		# Power status capture
		sensors['power'] = check_power()

	if 'water' in io['input']:
		# Water detection capture
		sensors['water'] = check_water()

	if 'button' in io['input']:
		# button detection capture
		sensors['button'] = check_button()

	if 'pir' in io['input']:
		# Motion detection capture
		sensors['motion'] = check_motion()

	if 'power' in io['input']:
		# Power status capture
		sensors['power'] = check_power()

	if 'dial' in io['input']:
		# Power status capture
		sensors['dial'] = check_dial()

	# What is our sensors dictionary looking like?
	print "  sensors: %s"% sensors

	trigger_outputs(0)
	for i in range(0,1):
		trigger_outputs(1)
		time.sleep(0.005)
		trigger_outputs(0)
		time.sleep(0.005)

	# This is just a temporary work around at the moment.
	#
	while (sensors['epoch']+1 > int(time.time())):
		#print "%s > %s?"% (sensors['epoch']+5, int(time.time()))
		time.sleep(0.1)



def doLoop():
	while True:
		try:
			cycle_sensors()
		except IOError:
			print "Error"
		except KeyboardInterrupt:
			print "Exit requested"
			reset()
		except SystemExit:
			print "System Exit requested"
			reset()
		except TypeError:
			print "Type Error!"

def sigterm_handler(signum, frame):
        print >> sys.stderr, "Exit received"
        sys.exit(0)

# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	set_io_ports()
	doLoop()
