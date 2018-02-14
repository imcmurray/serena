#!/bin/bash

# Jul 17 2017, this will provide information for multiple sites

now=$(date)
echo $now > /tmp/stats.out

uuids=$(/home/pi/Serena/redis-bash/redis-bash-cli hgetall uuids)
	for eachsite in $uuids; do
	if [ ${#eachsite} -gt 35 ]
	then
	#echo $eachsite;
	testsite="active_uuids:"$eachsite
	#echo $testsite;
	epochLast=$(/home/pi/Serena/redis-bash/redis-bash-cli hget $testsite epoch)
	#echo $epochLast;
	epochNow=$(date +%s)
	#echo $epochNow
	timeSince=$((epochNow-$epochLast))
	#echo $timeSince
	thresEpoch=$(/home/pi/Serena/redis-bash/redis-bash-cli hget $eachsite:threshold:scheduler last_executed)
	#echo $thresEpoch
	timeSinceThres=$((epochNow-$thresEpoch))
	#thisSite="[LHB:$timeSince/LTS:$timeSinceThres] on $eachsite"
	siteName=$(/home/pi/Serena/redis-bash/redis-bash-cli hget uuids $eachsite)

	cpu1=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange $eachsite:sensors:serenaTemp -1 -1 | cut -d : -f2)
	temp=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange $eachsite:sensors:temperature -1 -1 | cut -d : -f2)
	humidity=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange $eachsite:sensors:humidity -1 -1 | cut -d : -f2)
	power=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange $eachsite:sensors:power -1 -1 | cut -d : -f2)

	echo "[Site: $siteName]" >> /tmp/stats.out

	cpuF=$(echo $cpu1*9/5+32 | bc)
	echo "CPU Temp: $cpuF F" >> /tmp/stats.out
	tempF=$(echo $temp*9/5+32 | bc)
	echo "Room Temp: $tempF F" >> /tmp/stats.out
	echo "Humidity: $humidity %" >> /tmp/stats.out
	if [ $power ] 
	then
	if [ $power -gt 0 ]
	then
		echo "Power: OFF!!!" >> /tmp/stats.out
	else
		echo "Power: OK" >> /tmp/stats.out
	fi
	fi

        if [ $timeSince -gt 30 ]
        then
        	if [ $timeSinceThres -gt 30 ]
		then
        		echo "SC[!!:$timeSince]:TS[!!:$timeSinceThres]" >> /tmp/stats.out
		else
        		echo "SC[!!:$timeSince]:TS[OK:$timeSinceThres]" >> /tmp/stats.out
		fi
        else
        	if [ $timeSinceThres -gt 30 ]
		then
        		echo "SC[OK:$timeSince]:TS[!!:$timeSinceThres]" >> /tmp/stats.out
		else
        		echo "SC[OK:$timeSince]:TS[OK:$timeSinceThres]" >> /tmp/stats.out
		fi
        fi

	#echo "$eachsite" >> /tmp/stats.out

	fi
	done;



