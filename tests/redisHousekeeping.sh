#!/bin/bash

# Aug 14 2017 Need to clear up old redis keys, especally sorted sets.
# This is an temporary solution
# Execute from the root crontab

max_records_to_keep=2000

# Redis memory usage before
memory_before=$(/usr/local/bin/redis-cli --raw info memory | grep "used_memory_human")
echo $memory_before

# Sensor values
redis_keys=$(/usr/local/bin/redis-cli --raw keys *:sensors:*)
for redis_key in $redis_keys; do
	key_type=$(/usr/local/bin/redis-cli --raw type $redis_key)
	if [ $key_type = "zset" ]
	then
		number_records=$(/usr/local/bin/redis-cli --raw zcard $redis_key)
		echo $redis_key[$key_type:$number_records]
		if [ $number_records -gt $max_records_to_keep ]
		then
			# Clear out old data
			housekeeping_records_removed=$(/usr/local/bin/redis-cli zremrangebyrank $redis_key 0 -$max_records_to_keep)
			if [ $housekeeping_records_removed -gt 1 ]
			then
				echo "    Removed $housekeeping_records_removed records"
			fi
		fi
	fi
done

# AVG values
redis_keys=$(/usr/local/bin/redis-cli --raw keys *Avg*)
for redis_key in $redis_keys; do
	key_type=$(/usr/local/bin/redis-cli --raw type $redis_key)
	if [ $key_type = "zset" ]
	then
		number_records=$(/usr/local/bin/redis-cli --raw zcard $redis_key)
		echo $redis_key[$key_type:$number_records]
		if [ $number_records -gt $max_records_to_keep ]
		then
			# Clear out old data
			housekeeping_records_removed=$(/usr/local/bin/redis-cli zremrangebyrank $redis_key 0 -$max_records_to_keep)
			if [ $housekeeping_records_removed -gt 1 ]
			then
				echo "    Removed $housekeeping_records_removed records"
			fi
		fi

	fi
done

# Captured images
redis_keys=$(/usr/local/bin/redis-cli --raw keys *:capturedI*)
for redis_key in $redis_keys; do
	key_type=$(/usr/local/bin/redis-cli --raw type $redis_key)
	if [ $key_type = "zset" ]
	then
		number_records=$(/usr/local/bin/redis-cli --raw zcard $redis_key)
		echo $redis_key[$key_type:$number_records]
		if [ $number_records -gt $max_records_to_keep ]
		then
			# Clear out old data
			housekeeping_records_removed=$(/usr/local/bin/redis-cli zremrangebyrank $redis_key 0 -$max_records_to_keep)
			if [ $housekeeping_records_removed -gt 1 ]
			then
				echo "    Removed $housekeeping_records_removed records"
			fi
		fi
	fi
done



# Redis memory usage After
memory_after=$(/usr/local/bin/redis-cli --raw info memory | grep used_memory_human)
echo $memory_after

