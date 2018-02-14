#!/bin/sh

# Need to wait for Redis to come online before we start other Serena processes

PONG=`redis-cli ping |grep PONG`
echo $PONG
while [ "$PONG" != "PONG" ]
	do
		echo -n "."
	        sleep 1
	        PONG=`redis-cli ping |grep PONG`
	done

# Before we consider starting Serena, has there been a configuration update?
# Hmmm... we don't know out site_uuid at this point...
# so compare our MAC address with the MAC addresses for each site
# (a new serena site won't have a MAC address set in serena.local until serena-setup has executed on this device)
this_mac_address=$(cat /sys/class/net/eth0/address)
mac_hit=0
perform_update=0
count_sites=0
site_uuid_to_update=0

uuids=$(/usr/local/bin/redis-cli --raw -h serena.local hkeys uuids)
for eachsite in $uuids; do
  if [ ${#eachsite} -eq 36 ]
  then
    echo "Looking for MAC address match in $eachsite"
    count_sites=$((count_sites+1))
    devicepath=$eachsite":config:device"
    redis_mac_address=$(/usr/local/bin/redis-cli --raw -h serena.local hget $devicepath mac_address)
	
    if [ ${#redis_mac_address} -gt 10 ]
    then
      echo "  Found the MAC address of $redis_mac_address on serena.local"

      if [ "$redis_mac_address" = "$this_mac_address" ]
      then
        # We've found the right site configuration
        mac_hit=1
        echo "    Found a site and MAC address match, has an update been requested?"
        update_required=$(/usr/local/bin/redis-cli --raw -h serena.local hget $devicepath update_required)
        if [ $update_required -eq '1' ]
        then
	  perform_update=1
          site_uuid_to_update=$eachsite
          echo "      Yes, perform configuration update..."
        else
          echo "      No update has been requested..."
	fi

      else
        echo "    MAC address doesn't match with serenal.local configuration, skipping"
      fi

    else
      echo "  No MAC address defined"
    fi
  fi
done;

echo "Counted $count_sites sites"

if [ $mac_hit -eq 1 ]
then
  if [ $perform_update -eq 1 ]
  then
    if [ ${#site_uuid_to_update} -eq 36 ]
    then
      # START TARGETED CONFIGURATIO UPDATE
      echo "executing targeted update for this site: $site_uuid_to_update"
      /usr/bin/python /home/pi/Serena/serena-setup/update_configuration.py -S $site_uuid_to_update
    fi
  else
    # NORMAL STARTUP

# Do we need to move over a new config.yaml file from Serena/serena-setup ?

    if [ -e /home/pi/Serena/serena-setup/config.yaml ]
    then
      mv /home/pi/Serena/serena-setup/config.yaml /home/pi/Serena/config.yaml
      echo "would copy serena-setup config to working serena"
    fi

# Check that Serena sensor cycle has a config file

    if [ -e /home/pi/Serena/config.yaml ]
    then
      echo "would start serena normally"
      # start rq workers first (now that redis is online)
      sudo /usr/bin/supervisorctl start rq-worker-thresholds
      sudo /usr/bin/supervisorctl start rq-worker-alarms
      sudo /usr/bin/supervisorctl start rq-worker-alerts
      sudo /usr/bin/supervisorctl start rq-worker-responses
      sudo /usr/bin/supervisorctl start rq-worker-remote

      # start the sensor capture
      sudo /usr/bin/supervisorctl start serena-sensors-cycle

      # Finally start the threshold scheduler
      sudo /usr/bin/supervisorctl start serena-thresholds-scheduler
    else
      echo "would start serena-setup"
      # Enter Serena's setup phase
      sudo /usr/bin/supervisorctl start serena-setup
    fi
 fi
else
  # NEW SITE SETUP
  echo "would start serena-setup"
  sudo /usr/bin/supervisorctl start serena-setup
fi

# Serena-setup will monitor for available sites to be selected
# if no site is available then it will poll serena.local every few seconds to see
# if one has been created that it can use to configure the device
# So we can simply sun serena-setup if we get this far...
echo "ALL DONE!"

exit;


# Do we need to move over a new config.yaml file from Serena/serena-setup ?
#
#if [ -e /home/pi/Serena/serena-setup/config.yaml ]
#then
#	mv /home/pi/Serena/serena-setup/config.yaml /home/pi/Serena/config.yaml
#fi
#
## Check that Serena sensor cycle has a config file
#
#if [ -e /home/pi/Serena/config.yaml ]
#then
#	# start rq workers first (now that redis is online)
#	sudo /usr/bin/supervisorctl start rq-worker-thresholds
#	sudo /usr/bin/supervisorctl start rq-worker-alarms
#	sudo /usr/bin/supervisorctl start rq-worker-alerts
#	sudo /usr/bin/supervisorctl start rq-worker-responses
#	sudo /usr/bin/supervisorctl start rq-worker-remote
#
#	# start the sensor capture
#	sudo /usr/bin/supervisorctl start serena-sensors-cycle
#
#	# Finally start the threshold scheduler
#	sudo /usr/bin/supervisorctl start serena-thresholds-scheduler
#else
#	# Enter Serena's setup phase
#	sudo /usr/bin/supervisorctl start serena-setup
#fi
