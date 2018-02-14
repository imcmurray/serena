#!/usr/bin/python

import argparse,socket,redis,time

def get_args():
	# Assign description to the help doc
	parser = argparse.ArgumentParser(
			description='Script to test connectivity with Redis running on partem.us over sPiped')
	# Add arguments
	parser.add_argument(
			'-H', '--host', type=str, help='Host name or IP', required=True)
	parser.add_argument(
			'-P', '--port', type=int, help='Port number', required=True)
	parser.add_argument(
			'-A', '--auth', type=str, help='Auth password', required=True, default=None)
	parser.add_argument(
			'-D', '--database', type=int, help='Database number', required=True)
	# Array for all arguments passed to script
	args = parser.parse_args()
	# Assign args to variables
	host = args.host
	port = args.port
	auth = args.auth
	database = args.database
	# Return all variable values
	return host, port, auth, database

# Match return values from get_arguments()
# and assign to their respective variables
host, port, auth, database = get_args()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex((host, port))

if result == 0:

	# Connect to REDIS
	r_server = redis.Redis(host=host,
				port=port,
				password=auth,
				db=database)

	# Begin some basic tests

	# String
	r_server.set('test_key', 'test_value')
	print 'previous set key ' + r_server.get('test_key')

	# Integer
	r_server.set('counter', 1) 		#set an integer to a key
	print 'the counter set to: %s'% r_server.get('counter') 
	r_server.incr('counter') 		#increase the key value by 1, has to be int
	print 'the counter was increased! '+ r_server.get('counter') 
	r_server.decr('counter')		#we decrease the key value by 1, has to be int
	print 'the counter was decreased! '+ r_server.get('counter')

	# List 
	r_server.rpush('list1', 'element1')	#we use list1 as a list and push element1 as its element
	r_server.rpush('list1', 'element2')	#assign another element to our list
	r_server.rpush('list2', 'element3')	#the same
	print 'our redis list length is: %s'% r_server.llen('list1')
	print 'position 1 of our list is: %s'% r_server.lindex('list1', 1) 
	print 'list1 contents: %s'% r_server.lrange('list1', 0, -1)

	# Sets
	r_server.sadd('set1', 'el1')
	r_server.sadd('set1', 'el2')
	r_server.sadd('set1', 'el3')
	print 'the members of set1 are: %s'% r_server.smembers('set1')
	print 'set1 contains: %s elements'% r_server.scard('set1')
	print 'and a random element is: %s'% r_server.srandmember('set1')

	# Hash
	d = {'a':1, 'b':7, 'foo':'bar', 'dataset':{'foo':'bar'}}
	r_server.hmset('hash1', d)
	print 'contents of our hash are: %s'% r_server.hgetall('hash1')
	print 'value of foo: %s'% r_server.hget('hash1', 'foo')
	print 'value of hash1:dataset: %s'% r_server.hget('hash1', 'dataset')

	# Set the epoch
	r_server.hset('serena:counter:system', 'lastUpdate', int(time.time()))
	print 'Time stamp in epoch is: %s'% r_server.hget('serena:counter:system','lastUpdate')

else:
	print "\n!!!\nSPiped port 9080 is not open, cannot connect to Redis :("
