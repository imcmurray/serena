#!/bin/bash

# Startup script which determines what happens when the device is turned on
#
# Step 1:
#	Do we detect the config.yaml file in the setup directory?
#	(if the config.yaml file is found here then we assume the configuration has been updated)
#	If Yes:
#		- move /home/pi/Serena/setup/config.yaml to Serena's working directory (/home/pi/Serena)
#		- start up Serena Sensor Cycle (normal operation)
#	If No:
#		- Do we detect the config.yaml file in Serena's working directory? (/home/pi/Serena)
#		If Yes:
#			- start up Serena Sensor Cycle (normal operation)
#		If No: (execute serena-setup/setup.py) The rest of the logic (as shown here below) has been added to Serena's setup.py [Jul20-2017]
#			- Connect to Redis running on hostname 'Serena'
#			- Do we see any Serena sites defined in Serena[Redis]:uuids hash?
#			If Yes:
#				- Do we see the site (site_uuid) as being active in Serena[Redis]:active_uuids:{site_uuid}?
#				If Yes:
#					- skip the site from being selectable (since it is considered an active site on another device)
#				Else:
#					- start the site selector (showing only non-active sites)
#					- Are they any uuids to select?
#						If Yes:
#							- gather non-active uuids and display them to the user
#							- user selects a uuid and the configuration is written to the
#							  config.yaml file on the local device, in Serena's working directory (/home/pi/Serena)
#							- start up Serena Sensor Cycle (normal operation)
#	
#						If No:
#							- display message on LCD screen to setup site by visiting serena.local:8088
#							- wait 30 seconds
#							- extract any non-active uuids and present to user for selection
#							- loop through this display, wait logic until a site has been selected
#
# Note:
# Sites defined in Serena[Redis]:active_uuids:{site_uuid} expire after 30 seconds, unless maintained by an active Serena device.
# A Serena device is considered active when it is capturing sensor data. Part of the capturing sensor data process involves
# a Redis update to the active_uuids hash on the parent Serena device (running as hostname serena.local)
# This update refreshes the active_uuids record for each serena device. Redis will automatically delete these active_uuids records
# after 30 seconds. Therefore each Redis call to the parent Serena device resets the 30 seconds expiration time.
# That is how we maintain a list of active Serena devices. This list also helps filter available sites during a new Serena device setup.
#	

value=$(/usr/local/bin/redis-cli -h serena HGETALL uuids) # do a GET operation

#printf "\n--->%s<---\n" ${#value}

if [ ${#value} -gt 36 ] 
then
	# We have UUIDS defined 
	# So we can skip the configuration step
	# and show a selection of sites to pick from
	printf "Yahoo - we found uuids defined, which currently contains %s characters\n" ${#value}
else
	echo "Sorry - no UUIDs have been defined :("
fi

exec 6>&- # close the connection
#for each in $value; do
#printf "%s\n" $each;
#	if [ ${#each} == 36 ]
#	then
#		if [ ${#value} -gt 2 ]
#		then
#			printf "key >%s<\t\t value >%s<.\n" $each $value
#		fi
#	fi
#done;

