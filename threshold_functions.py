import requests, subprocess, os, sys, redis, time, socket 
from alarm_supervisor import startAlarm
from rq import Queue

# Define Globals
r_server = {}
q = {}

# Redis Parent globals
r_server_parent = {}
sock_parent = {}
result_parent = {}

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


def connect_to_redis_parent():
        global sock_parent,result_parent,r_server_parent

        # Connect to Parent REDIS (serena.local) Used for multi sites
        # Serena Sensors Cycles needs to update the active_uuids redis key
        r_server_parent = redis.Redis('serena.local', 6379)
        sock_parent = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result_parent = sock_parent.connect_ex(('serena.local', 6379))
        # A result_parent value of zero means no errors were encountered with the connection
        print 'result_parent returned: %s'% result_parent


def connect_to_redis():
        global r_server,q

        # Connect to REDIS
        r_server = redis.Redis()
        # Tell RQ which Redis connection to use
        q = Queue('alarms',connection=r_server)  # no args implies the default queue

def workoutAvg(sensor_data):
	#print "in workoutAvg"
	sensor_avg = []
	last_epoch = 0;
	for sensor_raw in sensor_data:
		# Split of the epoch
		sensor_epoch, sensor_value = sensor_raw.split(":")
		sensor_avg.append(float(sensor_value))
		last_epoch = sensor_epoch;
	sensor_avg_value = float("{0:.1f}".format(sum(sensor_avg)/len(sensor_avg)))
	print "found this to be the avg sensor value: %d"% sensor_avg_value
	return float(sensor_avg_value), last_epoch

def setRedisAvg(siteUUID, t_id, t_config, epoch, sensor_avg_value, trigger_clause, send_to_parent):
	global r_server, r_server_parent
	#print "in setRedisAvg"
	# set historical value - just epoch and value (used for graphs)
	r_server.zadd(siteUUID+':histAvgValue:'+t_id, str(epoch)+":"+str(sensor_avg_value), epoch)
	# set last value, with extra trigger information for use in the dashboard (status page)
	r_server.hmset(siteUUID+':lastAvgValue:'+t_id,
		{'epoch':str(epoch),'avgValue':str(sensor_avg_value),'triggerClause':str(trigger_clause),'redis_key':str(t_config['redis_key']),
		'triggerName':str(t_config['name']),'triggerValue':str(t_config[trigger_clause]),'triggerIcon':str(t_config['icon'])})
	if send_to_parent == 1:
		# also send the values to the parent serena device
		connect_to_redis_parent()
		print 'Saving to r_server_parent'
		r_server_parent.zadd(siteUUID+':histAvgValue:'+t_id, str(epoch)+":"+str(sensor_avg_value), epoch)
		# set last value, with extra trigger information for use in the dashboard (status page)
		r_server_parent.hmset(siteUUID+':lastAvgValue:'+t_id,
			{'epoch':str(epoch),'avgValue':str(sensor_avg_value),'triggerClause':str(trigger_clause),'redis_key':str(t_config['redis_key']),
			'triggerName':str(t_config['name']),'triggerValue':str(t_config[trigger_clause]),'triggerIcon':str(t_config['icon'])})


def startThresholdChecker(s_location, t_id, t_config, send_to_parent):
	global r_server,r_server_parent,q

	# Connect to redis
	connect_to_redis()

	# Extract the siteUUID
	siteUUID = s_location.split(':')[0]

	# find use the mincycles value from t_config to gather past sensor data
	if r_server.exists(s_location):
		min_cycles = int(t_config['mincycles'])*-1
		sensor_data = r_server.zrange(s_location, min_cycles, -1)
		if sensor_data:
			# perform a simple operation for testing
			f = open('/tmp/threshold_checker.log', 'a')
			write_this = '[%s] [%s]: '% (t_id,s_location)
			#write_this = 'Threshold in trigger [%s] [%s] [minCycles: %s]:\n\t%s\nredis:data: >>%s<<\n'% (t_id,s_location,min_cycles, t_config, sensor_data)
			f.write(write_this)
			#f.close()

			# Let's keep the average sensor value in Redis?
			# next version... TODO!

			# So we have the data in sensor_data, what are we going to do with it?
			# Work on what thr threshold has defined
			# The UI should only allow the user to input one value only
			# so the threshold is based on with the user wants:
			# 1 - An exact match (t.config.matchvalue)
			# 2 - A Value above the max (t.config.max)
			# 3 - A Value below the max (t.config.min)
			write_this_too = ""
			write_this_three = ""

			if 'matchvalue' in t_config:
				avg_sensor_through_cycle, last_epoch = workoutAvg(sensor_data)
				setRedisAvg(siteUUID, t_id, t_config, last_epoch, avg_sensor_through_cycle, 'matchvalue', send_to_parent)
				write_this_one = "MATCHVALUE: %s, AVG: %s, over %s cycles at %s\n"% (t_config['matchvalue'],avg_sensor_through_cycle, t_config['mincycles'], last_epoch)
				if float(avg_sensor_through_cycle) == float(t_config['matchvalue']):
					write_this_too = "\tfound exact value %s at last epoch [%s]\n"% (avg_sensor_through_cycle, last_epoch)
					job = q.enqueue_call(func=startAlarm,
                                                        args=(siteUUID, t_id, t_config),
                                                        timeout=60,
                                                        ttl=180,
                                                        at_front=1)
					write_this_three='Job called - well - should have been!\nJob: %s'% job

			elif 'max' in t_config:
				avg_sensor_through_cycle, last_epoch = workoutAvg(sensor_data)
				setRedisAvg(siteUUID, t_id, t_config, last_epoch, avg_sensor_through_cycle, 'max', send_to_parent)
				write_this_one = "MAX: %s, AVG: %s, over %s cycles at %s\n"% (t_config['max'],avg_sensor_through_cycle, t_config['mincycles'], last_epoch)
				if avg_sensor_through_cycle >= float(t_config['max']):
					write_this_too = "\tfound MAX value %s at last epoch [%s]\n"% (avg_sensor_through_cycle, last_epoch)
			elif 'min' in t_config:
				avg_sensor_through_cycle, last_epoch = workoutAvg(sensor_data)
				setRedisAvg(siteUUID, t_id, t_config, last_epoch, avg_sensor_through_cycle, 'min', send_to_parent)
				write_this_one = "MIN: %s, AVG: %s, over %s cycles at %s\n"% (t_config['min'],avg_sensor_through_cycle, t_config['mincycles'], last_epoch)
				if avg_sensor_through_cycle <= float(t_config['min']):
					write_this_too = "\tfound MIN value %s at last epoch [%s] trigger specifies MIN: %s\n"% (avg_sensor_through_cycle, last_epoch, t_config['min'])

			f.write(write_this_one)
			f.write(write_this_too)
			f.write(write_this_three)
			f.close()

			# set last executed epoch for this threshold check
			siteUUID = s_location.split(':')
			r_server.hset(siteUUID[0]+':threshold:scheduler', t_id, int(time.time()))

			if send_to_parent == 1:
				# also send the values to the parent serena device
				connect_to_redis_parent()
				print 'Saving threshold:scheduler to r_server_parent'
				r_server_parent.hset(siteUUID[0]+':threshold:scheduler', t_id, int(time.time()))

			# Clean up sensor data to the last 1000 entries
			r_server.zremrangebyrank(s_location,0,-1000)
	else:
		# no sensor data found so set the epoch that we checked for it at least!
		r_server.hset(siteUUID+':threshold:scheduler', t_id, int(time.time()))
		

	return

