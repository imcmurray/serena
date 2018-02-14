import redis,time
from rq import Queue
from rq_def_modules import count_words_at_url,sendSMS

# Connect to REDIS
r_server = redis.Redis(host='127.0.0.1',
			port='6379')

# Tell RQ which Redis connection to use
q = Queue(connection=r_server)  # no args implies the default queue

# Delay execution of count_words_at_url('http://nvie.com')
#job = q.enqueue(count_words_at_url, 'http://google.com')
#print job.result   # => None
#print "Job: %s"% job

job = q.enqueue(sendSMS, '+18082341234', '10th Test Message sent from Queue!')

print "Job: %s"% job

# Just for fun we want to see if the job finished here
# wouldn't normally wait for it to finish since we're shipping the job off
# to another external process so we can go back to doing what we need to do
# --- sleep until result 
# This will block the process and issue a redis HGET request as specified in the sleep
#while not job.result:
#	time.sleep(1)
time.sleep(5)
print job.result # Output of the python def
print "Job: %s"% job


