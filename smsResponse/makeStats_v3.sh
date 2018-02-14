#!/bin/bash

# Jul 28 2017, this will provide information for multiple sites, using the serena parent as the source of all data
# Looping through each detected trigger for each site

now=$(date)
echo $now > /tmp/stats.out
# Keeping the above so we can see when the last time this was requested

uuids=$(/usr/local/bin/redis-cli --raw hkeys uuids)
	for eachsite in $uuids; do
	if [ ${#eachsite} -eq 36 ]
	then
	#echo $eachsite;
	testsite="active_uuids:"$eachsite
	#echo $testsite;
	epochLast=$(/usr/local/bin/redis-cli --raw hget $testsite epoch)
	echo $epochLast;
	echo $now > /tmp/$eachsite-stats.out
	#thisSite="[LHB:$timeSince/LTS:$timeSinceThres] on $eachsite"
	siteName=$(/usr/local/bin/redis-cli --raw hget uuids $eachsite)
	echo "[Site: $siteName]" >> /tmp/$eachsite-stats.out

if [ $epochLast -eq -1 ]
then
	echo "Site $eachsite is no longer active!"
	epochNow=$(date +%s)
	thresEpoch=$(/usr/local/bin/redis-cli --raw hget $eachsite:threshold:scheduler last_executed)
	timeSinceThres=$((epochNow-$thresEpoch))
	echo "Is no longer active!!! Last seen $timeSinceThres seconds ago!" >> /tmp/$eachsite-stats.out
else
	epochNow=$(date +%s)
	#echo $epochNow
	timeSince=$((epochNow-$epochLast))
	#echo $timeSince
	thresEpoch=$(/usr/local/bin/redis-cli --raw hget $eachsite:threshold:scheduler last_executed)
	#echo $thresEpoch
	timeSinceThres=$((epochNow-$thresEpoch))
	triggerpath=$eachsite":lastAvgValue:triggers-*"
	histtriggerpath=$eachsite":histAvgValue:triggers-*"

	echo "Cycle through the triggers"
	done_power=0;
	done_roomtemp=0;
	done_cputemp=0;
	done_water=0;
	done_humidity=0;
	done_motion=0;
	triggers=$(/usr/local/bin/redis-cli --raw keys $triggerpath)
	for trigger in $triggers; do
		echo "Found Trigger: $trigger"

		rediskey=$(/usr/local/bin/redis-cli --raw hget $trigger redis_key)
		triggervalue=$(/usr/local/bin/redis-cli --raw hget $trigger avgValue)
		echo $rediskey" is currently: "$triggervalue

		if [ $rediskey == 'serenaTemp' ] 
		then
			if [ $done_cputemp -eq 0 ]
			then
				cpuF=$(echo $triggervalue*9/5+32 | bc)
				echo "CPU Temp: $cpuF F" >> /tmp/$eachsite-stats.out
				done_cputemp=1;
			fi
		fi

		if [ $rediskey == 'temperature' ] 
		then
			if [ $done_roomtemp -eq 0 ]
			then
				cpuF=$(echo $triggervalue*9/5+32 | bc)
				echo "Room Temp: $cpuF F" >> /tmp/$eachsite-stats.out
				done_roomtemp=1;
			fi
		fi

		if [ $rediskey == 'humidity' ] 
		then
			if [ $done_humidity -eq 0 ]
			then
				echo "Humidity: $triggervalue %" >> /tmp/$eachsite-stats.out
				done_humidity=1;
			fi
		fi

# Skipping motion because this needs a little more thought - Aug 2017
# Maybe we should use the last captured image rather than the hist values since we're comparing
# images for a percentage difference rather than just watching a sensor capture. The motion sensor
# can be tricked very easily since we have the PIR pointed towards A/C units.

		#if [ $rediskey == 'motion' ] 
		#then
			#if [ $done_motion -eq 0 ]
			#then
				#minus_one_grand=$((epochNow-1000))
				#histtrigger=${trigger//lastAvg/histAvg}
				##echo "History Trigger: $histtrigger" >> /tmp/detected.out
				#motions=$(/usr/local/bin/redis-cli --raw zrevrangebyscore $histtrigger $epochNow $minus_one_grand)
				#last_motion=0;
				#for detected in $motions; do
					##echo "Detected: $detected" >> /tmp/detected.out
					#if [[ $detected =~ ":1.0" ]]
					#then
						#last_motion=${detected//:1.0/}
						##echo "---> BREAK on $detected" >> /tmp/detected.out
						#break
					#fi
				#done
					
				#if [ $last_motion -gt 0 ]
				#then 
					#last_motion_seen=$((epochNow-$last_motion))
					#echo "Motion: $last_motion_seen seconds ago" >> /tmp/$eachsite-stats.out
				#else
					#echo "Motion: +1000 seconds ago" >> /tmp/$eachsite-stats.out
				#fi
				#done_motion=1;
			#fi
		#fi

		if [ $rediskey == 'power' ] 
		then
			if [ $done_power -eq 0 ]
			then
				done_power=1;
				if [ $triggervalue -gt 0 ]
				then
					echo "Power: OFF!" >> /tmp/$eachsite-stats.out
				else
					echo "Power: ON" >> /tmp/$eachsite-stats.out
				fi
			fi
		fi

	done;

        if [ $timeSince -gt 30 ]
        then
        	if [ $timeSinceThres -gt 30 ]
		then
        		echo "SC[!!:$timeSince]:TS[!!:$timeSinceThres]" >> /tmp/$eachsite-stats.out
		else
        		echo "SC[!!:$timeSince]:TS[OK:$timeSinceThres]" >> /tmp/$eachsite-stats.out
		fi
        else
        	if [ $timeSinceThres -gt 30 ]
		then
       			echo "SC[OK:$timeSince]:TS[!!:$timeSinceThres]" >> /tmp/$eachsite-stats.out
		else
        		echo "SC[OK:$timeSince]:TS[OK:$timeSinceThres]" >> /tmp/$eachsite-stats.out
		fi
        fi

	fi
fi
done;
	

