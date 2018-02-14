import requests, subprocess, os, sys, redis, time, ConfigParser
from rq import Queue
from ConfigParser import SafeConfigParser


# Define Globals
r_server = {}
q = {}
config = {}

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


def email_encrypted_file(filename, emailInfo):

        if os.path.isfile(filename):
                encrypt_cmd = subprocess.Popen(
                        "openssl smime -encrypt -aes256 -in "+filename+" -binary -outform DEM -out "+emailInfo['encrypted_filename']+" /home/pi/Serena/publickey.pem", 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        shell=True
                )
                try:
                        encrypt_cmd.communicate()
                except:
                        print 'Unable to encrypt file!'
                        return(1)
        else:
                print 'Original file not found! [%s]'% filename
                return(1)

        if os.path.isfile(emailInfo['encrypted_filename']):
                email_cmd = subprocess.Popen(
			"echo -e 'to:"+emailInfo['to']+"\nsubject:"+emailInfo['subject']+"\n"+emailInfo['msg']+"\n' | (cat - && uuencode "+emailInfo['encrypted_filename']+" motion_encrypted.bin) | ssmtp "+emailInfo['to'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True
                )

                try:
                        email_cmd.communicate()
                        return(0)
                except:
                        print 'Unable to email encrypted file!'
                        return(1)
        else:
                print 'Encrypted file not found!'
                return(1)


def email_file(filename, emailInfo):

        if os.path.isfile(filename):
                email_cmd = subprocess.Popen(
			"echo -e 'to:"+emailInfo['to']+"\nsubject:"+emailInfo['subject']+"\n"+emailInfo['msg']+"\n' | (cat - && uuencode "+filename+" motion.jpeg) | ssmtp "+emailInfo['to'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=True
                )

                try:
                        email_cmd.communicate()
                        return(0)
                except:
                        print 'Unable to email file!'
                        return(1)
        else:
                print 'file not found!'
                return(1)



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


def startAlert(siteUUID, t_id, t_config):
	# FIX ME
	global r_server,q

	load_configuration()

	# Connect to redis
	connect_to_redis()

	f = open('/tmp/alert.log', 'a')
	write_this = 'startAlert for trigger: [%s]\n'% t_id
	f.write(write_this)

	# Is the alert already in Redis
	# Yes? Is their already a job active and running to handle it?
	# 	Then exit, nothing for us to do, another process is already handling it
	# No - Create the entry in Redis
	# 	Start the alarm job for the passed in trigger (t_id)

	alarmRedisLocation = siteUUID+":Alert:"+t_id
	if r_server.exists(alarmRedisLocation):
		startEpoch = r_server.hget(alarmRedisLocation, 'alarmStartEpoch')
		secondsToLive = int(time.time())-int(startEpoch)
		confSecondsToHoldAlarm = config.get('option-alert','secondsheld');
		if secondsToLive >= confSecondsToHoldAlarm:
			f.write('\tAlert has expired!\n')
		else:
			f.write('\tAlert is still active! TTL:%s\n'% secondsToLive)
	else:
		# Create Alert
		f.write('\tAlert not found, need to create a new one\n')
		# Start Alert job

	# What is the status of the alarm?

	# Do we have any other alarms?

	f.close()

	return

