#!/bin/sh
from=$SMS_1_NUMBER
message=$SMS_1_TEXT
reply=""

if test "$message" = "Ping"; then
	reply="Pong!"
elif test "$message" = "Pong"; then
	reply="Now that's just silly!"
elif test "$message" = "Status"; then
	#reply="Status feature not yet implemented v3!"
	/home/pi/Serena/smsResponse/makeStats_v3.sh
	RESULT=$(cat /tmp/stats.out)
	reply="$RESULT"
elif test "$message" = "OK"; then
	reply="Acknowledgment feature not yet implemented!"
else
	reply="Send me a Ping"
fi

echo "$reply" | sudo gammu sendsms TEXT "$from"
