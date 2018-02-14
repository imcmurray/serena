#!/bin/sh
from=$SMS_1_NUMBER
message=$SMS_1_TEXT
reply=""

if test "$message" = "Ping"; then
	reply="Pong!"
	echo "$reply" | sudo gammu sendsms TEXT "$from"
elif test "$message" = "Pong"; then
	reply="Now that's just silly!"
	echo "$reply" | sudo gammu sendsms TEXT "$from"
elif test "$message" = "Status"; then
	rm -f /tmp/*-stats.out 2> /dev/null
	/home/pi/Serena/smsResponse/makeStats_v3.sh
	statfiles=$(ls -1 /tmp/*-stats.out)
        for statfile in $statfiles; do
		RESULT=$(cat $statfile)
		reply="$RESULT"
		echo "$reply" | sudo gammu sendsms TEXT "$from"
	done;
elif test "$message" = "SKIP"; then
	reply="Muting serena for 8 hours."
	skip=$(/usr/local/bin/redis-cli --raw hset ee091426-cfbf-4e81-9ef1-bed32eba18aa:responses:checkstatus skip 1)
	expire=$(/usr/local/bin/redis-cli --raw expire ee091426-cfbf-4e81-9ef1-bed32eba18aa:responses:checkstatus 28800)
	echo "$reply" | sudo gammu sendsms TEXT "$from"
elif test "$message" = "SKIP1"; then
	reply="Muting serena1 for 8 hours."
	skip=$(/usr/local/bin/redis-cli --raw hset 4cde46b5-72d9-4dfc-a1f1-8372dd9a33ce:responses:checkstatus skip 1)
	expire=$(/usr/local/bin/redis-cli --raw expire 4cde46b5-72d9-4dfc-a1f1-8372dd9a33ce:responses:checkstatus 28800)
	echo "$reply" | sudo gammu sendsms TEXT "$from"
elif test "$message" = "OK"; then
	reply="Acknowledgment feature not yet implemented!"
	echo "$reply" | sudo gammu sendsms TEXT "$from"
else
	reply="Send me a Ping"
	echo "$reply" | sudo gammu sendsms TEXT "$from"
fi

