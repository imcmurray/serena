import socket,redis,time,math,ConfigParser,sys,signal,os,ast,threading
from ConfigParser import SafeConfigParser
from rq import Queue
from alarm_functions import send_capture_request, capturePicture, compareImages
from alert_functions import startAlert, email_encrypted_file, email_file

# Alarm Supervisor
#
# Is brought to life by a Threshold Checker (worker) and should exist for the duration of an alarm
# If the alarm process dies .... without completeing it's supervisory workload ... need to think about that
# Maybe the threshold checker can check for the existance of the alarm and keep sending it through here
# and the supervisor determines if it's already got it running, or needs to reschedule to replace ...
# --- When an alarm is created, it exists for a maximum amount of time "secondsHeld = 1200" in the site config
# We'll create a Redis element that will maintain the alarm for that amount of time
# and reschedule it if the time expires ... need more thought on this process
#

# Define Globals
r_server = {}
config = {}
q = {}
qalert = {}
redis_sensor_path = ''
siteUUID = ''

class Listener(threading.Thread):
    def __init__(self, r, channels):
        threading.Thread.__init__(self)
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels)
    
    def work(self, item):
	fName = "/tmp/"+item['channel']+".log"
	#print item['channel'], ":", item['data']
       	f = open(fName, 'a')
	f.write('A: %s\n'% item)
	f.close()
    
    def run(self):
	while True:
		item = self.pubsub.get_message()
		print "item: %s"% item
		if item:
			if item['data'] == "KILL":
				self.pubsub.unsubscribe()
				break
			else:
				self.work(item)
		time.sleep(0.1)


def startAlarm(siteUUID, t_id, t_config):
        global r_server,config,q,qalert

	# initialize
        load_configuration()
        connect_to_redis()
        alarmRedisLocation = siteUUID+":Alarm:"+t_id
	# get default seconds to hold alarm
	confSecondsToHoldAlarm = config.get('options-alert','secondsheld');
	# override if we have a define seconds to hold on the trigger
	triggerSecondsToHoldAlarm = config.get(t_id,'secondsheld');
	if triggerSecondsToHoldAlarm:
		confSecondsToHoldAlarm = triggerSecondsToHoldAlarm

        f = open('/tmp/alarm_supervisor.log', 'a')
        write_this = 'startAlarm for trigger: [%s]\n'% t_id
        f.write(write_this)

        # Is the alarm already in Redis
        # Yes? Is their already a job active and running to handle it?
        #       Then exit, nothing for us to do, another process is already handling it
        # No - Create the entry in Redis
        #       Start the alarm job for the passed in trigger (t_id)

        if r_server.exists(alarmRedisLocation):
                startEpoch = r_server.hget(alarmRedisLocation, 'alarmStartEpoch')
                secondsToLive = (int(confSecondsToHoldAlarm)-(int(time.time())-int(startEpoch)))
		# We're auto expiring the alarm after confSecondsToHoldAlarm
		# So this next if section is bogus
                #if secondsToLive >= confSecondsToHoldAlarm:
                #        f.write('\tAlarm has expired!\n')
                #else:
                f.write('\tAlarm is still active! TTL:%s\n'% secondsToLive)
        else:
                # Create Alarm
                f.write('\tAlarm [%s] not found, Need to create a new one... work to do.\n'% alarmRedisLocation)
        	pipe = r_server.pipeline()
	        pipe.hset(alarmRedisLocation, 'alarmStartEpoch', int(time.time()))
	        pipe.expire(alarmRedisLocation, confSecondsToHoldAlarm)
        	pipe.execute()
                f.write('\tAlarm created.\n')

		# Do we even need to alert, or just do something different?
		# responserequired in the trigger? then create an Alert, we need to tell somebody and have them respond

                f.write('\tt_config: %s\n'% t_config)

		if t_config['responserequired'] == 'true':
		
			f.write('\tResponse required, creating Alert\n')
	                # Start Alert job
			job = qalert.enqueue_call(func=startAlert,
				args=(siteUUID, t_id, t_config),
				timeout=60,
				ttl=180,
				at_front=1)
			f.write('\tAlert job: %s\n'% job)
			while not job.result:
				time.sleep(0.5)
			f.write('\tAlert job returned: %s\n'% job.result)
		else:
			f.write('\tResponse not required, no Alert needed\n')

		# Is this motion that caused the alarm?

		if t_config['redis_key'] == 'motion':
			filename = capturePicture(siteUUID)
			if filename:
				last_motion_image = []
				# Do we have an image to compare against?
				if r_server.exists(siteUUID+':capturedImages'):
					last_motion_image = r_server.zrange(siteUUID+':capturedImages', -1, -1)
					if os.path.exists(last_motion_image[0]):
						percent_of_img_diff = compareImages(last_motion_image[0], filename)
						print 'Found: %s of image difference'% percent_of_img_diff
						if percent_of_img_diff > 1.5:
							print 'Looks like we found actual motion!'
							# save filename to sorted set in redis
							r_server.zadd(siteUUID+':capturedImages', filename, int(time.time()))
							# send an email... encrypted of course!
							emailDict = {
								'to': 'serena.utb@gmail.com',
								'subject': 'Motion Detected: '+siteUUID,
								'msg': filename+' ['+str(percent_of_img_diff)+']',
								'encrypted_filename': '/tmp/'+siteUUID+'_'+str(int(time.time()))+'.bin'
							}
							print 'Sending encrypted email [%s]'% emailDict
							#email_encrypted_file(filename, emailDict)
							email_file(filename, emailDict)
						else:
							print 'Looks like we found a ghost!'
							os.remove(filename)
							#reset image wait since there was no actual visible movement!
			        			r_server.expire(alarmRedisLocation, 1)
					else:
						# File not found in path, save filename to sorted set in redis
						r_server.zadd(siteUUID+':capturedImages', filename, int(time.time()))
				else:
					# Nothing exists, so create the new one
					r_server.zadd(siteUUID+':capturedImages', filename, int(time.time()))
			else:
				# no filename returned to must be an error!
				print 'no filename returned from capturePicture!'

        	pubsubChannel = siteUUID+":pubsub:"+t_id
		f.write('\tStarting pubsub listen on channel: %s\n'% pubsubChannel)

		client = Listener(r_server, pubsubChannel)
		client.start()
		f.write('\tpubsub was closed\n')
    

	# Now that we have determined that an Alarm has been created
	# and an Alert has already been created (notification sent)
	# if response is required for this trigger then let's go in a loop, waiting for a response
	# The response will be updated here in the alarm supervisor as the alert being answered
	
	

        # What is the status of the alarm?

        # Do we have any other alarms?

        f.close()

        return

def reset_redis_alerts():
        global r_server
        pipe = r_server.pipeline()
        pipe.hset('alerts:serena', 'manually_overridden', '')
        pipe.hset('alerts:serena', 'lcd_message', '')
        pipe.hset('alerts:serena', 'acknowledged', '')
        pipe.hset('alerts:serena', 'last_acknowledgment', '')
        pipe.execute()


def load_configuration():
	global config, siteUUID
	try:
		config = SafeConfigParser()
		config.read('config.yaml')

		siteInitials = config.get('options-siteInfo','courtinitials');
		if siteInitials:
			# Update Site Counters
			print "Alarm Scheduler: siteInitials: %s"% siteInitials

	except ConfigParser.ParsingError, err:
		print 'Could not parse:', err


def connect_to_redis():
	global r_server,q,qalert

	# Connect to REDIS
	r_server = redis.Redis()
	# Tell RQ which Redis connection to use
	q = Queue('alarms',connection=r_server)  # no args implies the default queue
	qalert = Queue('alerts',connection=r_server)  # no args implies the default queue


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
			print 'last_schedule_executed: %s'% last_schedule_executed
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


def start_up():
	print "Alarm Supervisor started up"
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

	siteInitials = config.get('options-siteInfo','courtinitials');
	if siteInitials:
		# Update Site Counters
		print "siteInitials: %s"% siteInitials
	if config.has_section('options-redis'):
		if config.get('options-redis', 'sensor_path'):
			redis_sensor_path = config.get('options-redis', 'sensor_path') + ":" + siteInitials + ":"
			return 0
	return 1

def get_siteUUID():
	global redis_sensor_path, siteUUID
	siteUUID, t1, t2, t3 = redis_sensor_path.split(':')
	if len(siteUUID) == 36:
		print 'siteUUID: %s'% siteUUID
		return 0
	return 1

	
def cycle_redis():
	global config, r_server, q, redis_sensor_path, siteUUID
	
	# Could create queue jobs to check the threshold independantly instead of running them here...
	# Just add q to the global declaration for this function if we want to go that route

	print 'cycle_redis: %s'% int(time.time())
	last_scheduled = get_last_scheduled()
	print 'time difference from last scheduled: %s - %s = %s seconds'% (int(time.time()), (int(time.time())-last_scheduled), last_scheduled)
	set_last_scheduled()

	# check for early_warnings, they have priority over threshold checking
        redis_status = get_redis_alert_status()

        if redis_status['lcd_message']:
                if redis_status['acknowledged']:
                        # Acknowledged Alarm
                        print 'Serena has an acknowledges alarm, bypassing threshold checker'
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
							args=(sensor_location, threshold_id, threshold_config),
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
