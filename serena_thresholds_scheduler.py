#!/usr/bin/python

import socket,redis,time,math,ConfigParser,sys,signal,os,ast
from ConfigParser import SafeConfigParser
from rq import Queue
from threshold_functions import startThresholdChecker

# Threshold Scheduler
#
# Determine if we need to schedule a threshold checker job
# At the moment it will execute all of them...
# But the idea is that we could schedule certain thresholds to be checked
# more often than others, maybe using redis to capture the epoch of the last
# check and wait a certain amount of time to pass before scheduling another threshold check
# Maybe the duration of wait can be defined in the threshold configuration - todo later
#

# Define Globals
r_server = {}
config = {}
q = {}
redis_sensor_path = ''
siteUUID = ''
send_to_parent = -1

# Redis Parent globals
r_server_parent = {}


def load_configuration():
	global config, siteUUID
	try:
		config = SafeConfigParser()
		config.read('config.yaml')

		siteInitials = config.get('options-siteInfo','courtInitials');
		if siteInitials:
			# Update Site Counters
			print "siteInitials: %s"% siteInitials

	except ConfigParser.ParsingError, err:
		print 'Could not parse:', err


def connect_to_redis_parent():
	global r_server_parent
        r_server_parent = redis.Redis('serena.local', 6379)


def connect_to_redis():
	global r_server,q

	# Connect to REDIS
	r_server = redis.Redis()
	# Tell RQ which Redis connection to use
	q = Queue('thresholds',connection=r_server)  # no args implies the default queue


def get_redis_alert_status():
        global r_server
        message_for_lcd = r_server.hget('alerts:serena', 'lcd_message')
        acknowledged = r_server.hget('alerts:serena', 'acknowledged')
        return {'lcd_message': message_for_lcd,
                'acknowledged': acknowledged}


def get_last_scheduled(trigger_id=None):
        global r_server, siteUUID
	last_schedule_executed = 0
	if r_server.exists(siteUUID+':threshold:scheduler'):
		if trigger_id is None:
		        last_schedule_executed = r_server.hget(siteUUID+':threshold:scheduler', 'last_executed')
		else:
			if r_server.hexists(siteUUID+':threshold:scheduler', trigger_id):
			        last_schedule_executed = r_server.hget(siteUUID+':threshold:scheduler', trigger_id)
			else:
				set_last_scheduled(trigger_id)

		if int(last_schedule_executed)>0:
			#print 'last_schedule_executed: %s'% last_schedule_executed
			last_ran = (int(time.time()) - int(last_schedule_executed))
		        return last_ran
		else:
			return 0
	else:
		return 0


def set_last_scheduled(trigger_id=None):
        global r_server, siteUUID
	if trigger_id is None:
	        r_server.hset(siteUUID+':threshold:scheduler', 'last_executed', int(time.time()))
	else:
	        r_server.hset(siteUUID+':threshold:scheduler', trigger_id, int(time.time()))


def set_last_scheduled_parent(trigger_id=None):
        global r_server_parent, siteUUID
	connect_to_redis_parent()
	if trigger_id is None:
	        r_server_parent.hset(siteUUID+':threshold:scheduler', 'last_executed', int(time.time()))
	else:
	        r_server_parent.hset(siteUUID+':threshold:scheduler', trigger_id, int(time.time()))


def start_up():
	print "Threshold Scheduler started up"
	time_since_last = get_last_scheduled()
	print '\tLast Threshold Scheduler operation occurred : %s seconds ago'% time_since_last
	if get_sensor_path():
		print 'Unable to determine sensor path location in Redis, exiting'
		exit()
	if get_siteUUID():
		print 'Unable to locate siteUUID, exiting'
		exit()


def get_sensor_path():
	global config, redis_sensor_path, siteUUID

	siteInitials = config.get('options-siteInfo','courtInitials');
	if siteInitials:
		# Update Site Counters
		print "siteInitials: %s"% siteInitials
	if config.has_section('options-redis'):
		if config.get('options-redis', 'sensor_path'):
			#redis_sensor_path = config.get('options-redis', 'sensor_path') + ":" + siteInitials + ":"
			redis_sensor_path = config.get('options-redis', 'sensor_path') + ":"
			return 0
	return 1

def get_siteUUID():
	global redis_sensor_path, siteUUID
	siteUUID, t1, t2 = redis_sensor_path.split(':')
	if len(siteUUID) == 36:
		print 'siteUUID: %s'% siteUUID
		return 0
	return 1

	
def cycle_redis():
	global config, r_server, q, redis_sensor_path, siteUUID, send_to_parent
	
	# Could create queue jobs to check the threshold independantly instead of running them here...
	# Just add q to the global declaration for this function if we want to go that route

	#print 'cycle_redis: %s'% int(time.time())
	last_scheduled = get_last_scheduled()
	#print 'time difference from last scheduled: %s - %s = %s seconds'% (int(time.time()), (int(time.time())-last_scheduled), last_scheduled)
	set_last_scheduled()

	# workout if this device is the parent
	if send_to_parent == -1:
		print 'Redis parent is not determined'
		hostname = config.get('options-siteInfo','hostname')
	        parent_hostname = config.get('options-siteInfo','parenthostname')
		if hostname != parent_hostname:
			print 'Sending to Redis parent is now determined'
			send_to_parent = 1
			set_last_scheduled_parent()
		else:
			print 'No need to send to Redis parent'
			send_to_parent = 0
	elif send_to_parent == 1:
		set_last_scheduled_parent()

	# check for early_warnings, they have priority over threshold checking
        redis_status = get_redis_alert_status()

        if redis_status['lcd_message']:
                if redis_status['acknowledged']:
                        # Acknowledged Alarm
                        print 'Serena has an acknowledged alarm, bypassing threshold checker'
                else:
                        # Alarm active and unanwsered
                        print 'Serena has an active alarm!!! bypassing threshold checker'
        else:
                if redis_status['acknowledged']:
                        print 'Serena has been muted! bypassing threshold checker'
                else:
                        print 'Serena has nothing new to report, creating the threshold checker jobs'

			if config.has_section('identifiers'):
				tid = ast.literal_eval(config.get('identifiers','triggers'))
				# TODO we're using the variable name threshold_id but it's really the triger_id still - clean up
				for threshold_id in tid:
					print "Working on threshold in trigger: %s"% threshold_id
					threshold_config = dict(config.items(threshold_id))

					threshold_last_checked = get_last_scheduled(threshold_id)
					# threshold_last_checked is how long in seconds it hasn't been executed since the last time it was

					if ( int(threshold_last_checked) > int(threshold_config['mincycles']) ):
						sensor_location = redis_sensor_path+threshold_config['redis_key']
						print '\tNeed to schedule a threshold check in trigger:\n\t\t%s at location: {%s}'% (threshold_id,sensor_location)
						#print '\t\t\tthreshold_config: %s'% threshold_config
						job = q.enqueue_call(func=startThresholdChecker,
							args=(sensor_location, threshold_id, threshold_config, send_to_parent),
							timeout=60,
							ttl=180,
							at_front=0)
					else:
						print '\t\tSkipping threshold check since mincycles [%s] has not passed since last run [%s seconds remaining]'% (threshold_config['mincycles'], (int(threshold_config['mincycles'])-int(threshold_last_checked)))

	sleep_for = config.get('options-alert','secondsbetweenthresholdcheck')
	#print 'Sleeping for: %s'% sleep_for
	#time.sleep(int(sleep_for))
	#time.sleep(1)
	time_now = int(time.time())
	while (time_now == int(time.time())):
                time.sleep(0.3)


def doLoop():
	while True:
		try:
			cycle_redis()
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
        sys.exit(0)


# Bind our callback to the SIGTERM signal
signal.signal(signal.SIGTERM, sigterm_handler)

if __name__ == '__main__':
	#get_args()
	connect_to_redis()
	load_configuration()
	start_up()
	doLoop()
