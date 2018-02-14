#!/bin/bash

# Aug 14 2017 Newer versions of the Kernel are showing an i2c timed out error
# look for this in the GPIO status and reset as needed
# Execute from the root crontab

gpio_status=$(gpio -g read 8)
# Status of 1 is normal operation. If Status is ever 0, then we need to reset the board
if [ $gpio_status -lt 1 ]
then
	dateNow=$(date)	
	echo "$dateNow - Need to RESET the GrovePi [$gpio_status]" >> /tmp/GrovePi-Reset.log
	reset_command=$(avrdude -c gpio -p m328p)
	echo "$reset_command" >> /tmp/GrovePi-Reset.log
	exit
fi
 
# Check for repeated button presses

button_held=0
buttons=$(/usr/local/bin/redis-cli --raw zrevrange 4cde46b5-72d9-4dfc-a1f1-8372dd9a33ce:sensors:button 0 30)

for button in $buttons; do
	button_value="${button:(-1)}"
	if [ $button_value -eq 1 ]
	then
		((button_held++))
	fi
done

if [ $button_held -gt 20 ]
then
	dateNow=$(date)	
	echo "$dateNow - Need to RESET the GrovePi (too many button presses)" >> /tmp/GrovePi-Reset.log
	reset_command=$(avrdude -c gpio -p m328p)
	echo "$reset_command" >> /tmp/GrovePi-Reset.log
	exit
fi
