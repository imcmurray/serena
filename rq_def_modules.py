import requests, time
import subprocess
from picamera import PiCamera, Color

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


# count_words_at_url is a simple example of a python function which demonstates the queue process
def count_words_at_url(url):
    resp = requests.get(url)
    return len(resp.text.split())


def sendSMS(number, message):
	sms_cmd = subprocess.Popen( "sudo gammu-smsd-inject TEXT '"+number+"'", stdin=subprocess.PIPE, shell=True, stdout=subprocess.PIPE )
	outp = sms_cmd.communicate( message )
	return outp

def capturePicture(filename='/tmp/iantest.jpg'):
	camera = PiCamera()
	# Heat the camera up
	camera.rotation = 180
	camera.start_preview()
	camera.annotate_background = Color('blue')
	camera.annotate_foreground = Color('yellow')
	camera.annotate_text_size = 20
	now = time.strftime("%c")
	camera.annotate_text = " Serena [TRB]: %s "% now
	
	time.sleep(.5)
	camera.capture(filename)
	time.sleep(.5)
	camera.stop_preview()
	return

