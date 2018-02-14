#!/bin/bash

cpu1=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:serenaTemp -1 -1 | cut -d : -f2)
temp=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:temperature -1 -1 | cut -d : -f2)
power=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:power -1 -1 | cut -d : -f2)
uuids=$(/home/pi/Serena/redis-bash/redis-bash-cli hgetall uuids | cut -d : -f2)

for eachsite in $uuids; do
	if [ ${#eachsite} -gt 35 ]
	then
		echo $eachsite;
		testsite="active_uuids:"$eachsite
		echo "became: $testsite"
		epochLast=$(/home/pi/Serena/redis-bash/redis-bash-cli hget $testsite epoch)
		epochNow=$(date +%s)
		timeSince=$((epochNow-$epochLast))
		echo "Site: $eachsite, last seen $timeSince seconds ago."
	fi
done;

reply="Hello"

normalcpu=70.0
normaltemp=35.0

powerStatus=""
cpuStatus=""
tempStatus=""

sendIt = 0

if [ $power -gt 0 ]
then
	powerStatus="Power is OFF!"
	sendIt=1
else
	powerStatus="Power is ON :)"
fi

if [[ $normalcpu < $cpu1 ]]
then
	cpuStatus="Serena is HOT! $cpu1"
	sendIt=1
else
	cpuStatus="Serena is OK $cpu1"
fi

if [[ $normaltemp < $temp ]]
then
	tempStatus="Room is HOT! $temp"
	sendIt=1
else
	tempStatus="Room is OK $temp"
fi

#if [ $sendIt -gt 0 ]
#then
#	now=$(date)
#	reply="As of: $now $cpuStatus $tempStatus $powerStatus"
#	echo "$reply" | sudo gammu-smsd-inject TEXT '+18082341234'
#fi


