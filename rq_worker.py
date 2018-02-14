import redis,time
from rq import Queue
from rq_def_modules import count_words_at_url

# Connect to REDIS
r_server = redis.Redis(host='127.0.0.1',
			port='6379')

# Tell RQ what Redis connection to use
q = Queue(connection=r_server)  # no args implies the default queue

# Getting the number of jobs in the queue
print len(q)

# Retrieving jobs
queued_job_ids = q.job_ids # Gets a list of job IDs from the queue
queued_jobs = q.jobs # Gets a list of enqueued job instances
job = q.fetch_job('my_id') # Returns job having ID "my_id"

print "Q Job ID: %s"% queued_job_ids
print "  Q Jobs: %s"% queued_jobs
print "     Job: %s\n"% job
