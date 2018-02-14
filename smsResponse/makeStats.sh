#!/bin/bash

now=$(date)
echo $now > /tmp/stats.out

cpu1=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:serenaTemp -1 -1 | cut -d : -f2)
temp=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:temperature -1 -1 | cut -d : -f2)
humidity=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:humidity -1 -1 | cut -d : -f2)
power=$(/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:power -1 -1 | cut -d : -f2)

echo "CPU Temp: $cpu1" >> /tmp/stats.out
echo "Room Temp: $temp" >> /tmp/stats.out
echo "Humidity: $humidity" >> /tmp/stats.out
if [ $power -gt 0 ]
then
	echo "Power: OFF!!!" >> /tmp/stats.out
else
	echo "Power: OK" >> /tmp/stats.out
fi



#/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:serenaTemp -1 -1 >> /tmp/stats.out
#echo "Room Temp:" >> /tmp/stats.out
#/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:temperature -1 -1 >> /tmp/stats.out
#echo "Room Humidity:" >> /tmp/stats.out
#/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:humidity -1 -1 >> /tmp/stats.out
#echo "Power:" >> /tmp/stats.out
#/home/pi/Serena/redis-bash/redis-bash-cli zrange 65ae194f-0336-4b8f-972d-6803ea88f2f3:sensors:TRB:power -1 -1 >> /tmp/stats.out


