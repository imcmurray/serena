import requests, subprocess, os, sys, redis, time, errno
from rq import Queue
from picamera import PiCamera, Color
from itertools import izip
from PIL import Image


# Define Globals
r_server = {}
q = {}
config = {}
motionCapturedDirectory = '/home/pi/Serena/capturedMotion'

# Basic python functions which we can offload to the queue
# We're using python-rq so we can offload tasks to the queue
# and reduce the amount of blocking.
# http://python-rq.org/
#
# Ideas for queue usage:
#	- Notification escalations
# 	- Sensor threshold detection
#	- Alerts
#	- IT Responses
#		- Mute alerts
#		- Status requests
#
# Anything that we can offload to a specific worker and keep Serena's
# core function (sensor checking cycle) running as efficiently as possible



def sendSMS(number, message):
	sms_cmd = subprocess.Popen( "sudo gammu-smsd-inject TEXT '"+number+"'", stdin=subprocess.PIPE, shell=True, stdout=subprocess.PIPE )
	outp = sms_cmd.communicate( message )
	return outp

def load_configuration():
        global config
        try:
                config = SafeConfigParser()
                config.read('config.yaml')
        except ConfigParser.ParsingError, err:
                print 'Could not parse:', err


def connect_to_redis():
        global r_server,q

        # Connect to REDIS
        r_server = redis.Redis()
        # Tell RQ which Redis connection to use
        q = Queue('alerts',connection=r_server)  # no args implies the default queue


def send_capture_request(siteUUID, t_id, t_config, site_config):
	# FIX ME
	global r_server,q, config

	load_configuration()

	# Connect to redis
	connect_to_redis()

	f = open('/tmp/alarm_supervisor.log', 'a')
	write_this = 'startAlarm for trigger: [%s]\n'% t_id
	f.write(write_this)

	# Is the alarm already in Redis
	# Yes? Is their already a job active and running to handle it?
	# 	Then exit, nothing for us to do, another process is already handling it
	# No - Create the entry in Redis
	# 	Start the alarm job for the passed in trigger (t_id)

	alarmRedisLocation = siteUUID+":Alarm:"+t_id
	if r_server.exists(alarmRedisLocation):
		startEpoch = r_server.hget(alarmRedisLocation, 'alarmStartEpoch')
		secondsToLive = int(time.time())-int(startEpoch)
		confSecondsToHoldAlarm = config.get('option-alert','secondsheld');
		if secondsToLive >= confSecondsToHoldAlarm:
			f.write('\tAlarm has expired!\n')
		else:
			f.write('\tAlarm is still active! TTL:%s\n'% secondsToLive)
	else:
		# Create Alarm
		f.write('\tAlarm not found, creating new\n')
		# Start Alarm job

	# What is the status of the alarm?

	# Do we have any other alarms?

	f.close()

	return


def checkPath(path):
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise

def capturePicture(siteName):
	global motionCapturedDirectory
        camera = PiCamera()
        #camera.rotation = 90
        # Heat the camera up
        camera.start_preview()
        #camera.brightness = 50
        camera.annotate_background = Color('black')
        camera.annotate_foreground = Color('white')
        camera.annotate_text_size = 17
	nowNice = time.strftime("%c")
	nowRaw = time.strftime("%Y%m%d-%H%M%S")
	nowEpoch = int(time.time())
	checkPath(motionCapturedDirectory+"/"+siteName)
	filename = '%s/%s/%s.jpg'% (motionCapturedDirectory, siteName, nowRaw)	
        camera.annotate_text = 'Site:[%s] %s'% (siteName, nowNice)
        time.sleep(1)
        camera.capture(filename)
        time.sleep(.5)
        camera.stop_preview()
	# send filename back to caller
        return filename


def compareImages(img1,img2): 
	print 'img1: %s, img2: %s'% (img1, img2)
	i1 = Image.open(img1)
	i2 = Image.open(img2)
	assert i1.mode == i2.mode, "Different kinds of images."
	assert i1.size == i2.size, "Different sizes."
  
	pairs = izip(i1.getdata(), i2.getdata())
	if len(i1.getbands()) == 1:
		# for gray-scale jpegs
		dif = sum(abs(p1-p2) for p1,p2 in pairs)
	else:
		dif = sum(abs(c1-c2) for p1,p2 in pairs for c1,c2 in zip(p1,p2))
                  
	ncomponents = i1.size[0] * i1.size[1] * 3
	return (dif / 255.0 * 100) / ncomponents


