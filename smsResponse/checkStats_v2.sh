#!/bin/bash

# Jul 17 2017, this will provide information for multiple sites


uuids=$(/usr/local/bin/redis-cli --raw hkeys uuids)
for eachsite in $uuids; do
	if [ ${#eachsite} -eq 36 ]
	then
		#echo $eachsite;
		activesite="active_uuids:"$eachsite
		siteName=$(/usr/local/bin/redis-cli --raw hget uuids $eachsite)
		epochLast=$(/usr/local/bin/redis-cli --raw hget $activesite epoch)
		epochNow=$(date +%s)

		# Has this site processed thresholds? If so then we can consider it a once active site
		thresEpoch=$(/usr/local/bin/redis-cli --raw hget $eachsite:threshold:scheduler last_executed)

		if [ $thresEpoch -gt 1 ]
		then	
		
			timeSinceThres=$((epochNow-$thresEpoch))

			if [ $epochLast -eq -1 ] 
			# Active site is down! the redis active key was no longer found! ALERT!!!
			then

				if [ $timeSinceThres -gt 0 ]
				then 
					skip=$(/usr/local/bin/redis-cli --raw hget $eachsite:responses:checkstatus skip)
					if [ $skip -lt 0 ]
					then
						echo "Site: $siteName [$eachsite] is no longer active!!!"
						now=$(date)
						reply="[$siteName] is no longer active!!! Last seen $timeSinceThres seconds ago! $now [site_uuid:$eachsite]"
						echo "$reply" | sudo gammu-smsd-inject TEXT '+18082341234'
					fi
				fi
			else
				timeSince=$((epochNow-$epochLast))
				#thisSite="Site: $eachsite (LHB:$timeSince)"

				cpu1=$(/usr/local/bin/redis-cli --raw zrange $eachsite:sensors:serenaTemp -1 -1 | cut -d : -f2)
				temp=$(/usr/local/bin/redis-cli --raw zrange $eachsite:sensors:temperature -1 -1 | cut -d : -f2)
				power=$(/usr/local/bin/redis-cli --raw zrange $eachsite:sensors:power -1 -1 | cut -d : -f2)

				echo "cpu1:$cpu1"
				echo "temp:$temp"
				echo "power:$power"

				reply="Hello"

				normalcpu=70.0
				normaltemp=35.0

				powerStatus=""
				cpuStatus=""
				tempStatus=""
				sStatus=""

				sendIt=0

				if [ $power -gt 0 ]
				then
					powerStatus="Power is OFF!"
					sendIt=1
				else
					powerStatus="Power is ON"
				fi

				echo "normalcpu lt cpu1: $normalcpu $cpu1"
				cpuF=$(echo $cpu1*9/5+32 | bc)
				if (( $(echo "$normalcpu < $cpu1" |bc -l) )); then
					cpuStatus="Serena is HOT! $cpuF F"
					sendIt=1
				else
					cpuStatus="Serena is OK $cpuF F"
				fi

				tempF=$(echo $temp*9/5+32 | bc)
				if (( $(echo "$normaltemp < $temp" |bc -l) )); then
					tempStatus="Room is HOT! $tempF F"
					sendIt=1
				else
					tempStatus="Room is OK $tempF F"
				fi


				if [ $timeSince -gt 30 ]
				then
					sendIt=1
					if [ $timeSinceThres -gt 30 ]
					then
						sStatus="SC[!!:$timeSince]:TS[!!:$timeSinceThres]"
					else
						sStatus="SC[!!:$timeSince]:TS[OK:$timeSinceThres]"
					fi
				else
					if [ $timeSinceThres -gt 30 ]
					then
						sendIt=1
						sStatus="SC[OK:$timeSince]:TS[!!:$timeSinceThres]"
					else
						sStatus="SC[OK:$timeSince]:TS[OK:$timeSinceThres]"
					fi
				fi




				if [ $sendIt -gt 0 ]
				then
					now=$(date)
					reply="[$siteName] $cpuStatus, $tempStatus, $powerStatus, $sStatus $now"
					echo "$reply" | sudo gammu-smsd-inject TEXT '+18082341234'
				fi

			fi
		fi
	fi
done;
