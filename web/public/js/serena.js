var app = angular.module('serena', ['ngSanitize', 'ngCookies', 'ui.toggle']);

app.controller('siteController', ['$scope','$http','$cookies', function($scope, $http, $cookies) {
	console.log("Yeah Baby! Angular Loaded :)");
	$scope.hello = "Hello World! <b>Angular loaded!</b>";
	$scope.selectedTab = 0;
  $scope.notificationStyles = {
    "notificationStyles": [{
      "value": "all",
      "name": "Notify All Contacts"
    },
    {
      "value": "cascade",
      "name": "Cascade Down"
    }
    ]
  };
  $scope.audibleAlertTypes = {
    "audibleAlertTypes": [{
      "value": "none",
      "name": "Silent"
    },
    {
      "value": "beep",
      "name": "Single Short Beep"
    },
    {
      "value": "solid",
      "name": "Solid Tone"
    }
    ]
  };

	$scope.siteConfig = "";
	$scope.sensors = "";
	$scope.contacts = "";
	$scope.groups = "";
	$scope.triggers = "";
	$scope.message = "";
	$scope.site_uuid = "";
  $scope.saveConfigStatus = "";
  $scope.deleteSiteStatus = "";
	$scope.selectedPerson = {};
	$scope.selectedGroup = {};
	$scope.selectedTrigger = {};
	$scope.lastPersonClicked = 99;
	$scope.lastGroupClicked = {};
	$scope.lastTriggerClicked = {};
	
	site_config_section = "siteInfo";

	// get uuid from cookie
	var site_uuid = $cookies.get('serenaSiteUUID');
	console.log("Found the serenaSiteUUID cookie value of: " + site_uuid);

	$cookies.put("Hello", "World");
        console.log($cookies.getAll());

	if ( site_uuid && site_config_section ) {
	
		$http.get('/site-config2?uuid='+site_uuid+'&section='+site_config_section)
			.then(function (response) {

				var data = response.data;
				var status = response.status;
				var statusText = response.statusText;
				var headers = response.headers;
				var config = response.config;
        $scope.saveConfigStatus = 0;

				if ( data.status == "OK" ) {
					$scope.siteConfig = data.siteConfig;
				}
				
				console.log(data);
				$scope.site_uuid = site_uuid;
			});
	} else {
		console.log("serenaSiteUUID not found!");
	}

	$scope.saveConfiguration = function() {
		//console.log("Received a request to update the configuration with: " + JSON.stringify($scope.siteConfig));
		var dataObj = JSON.stringify($scope.siteConfig);
    $scope.saveConfigStatus = 1;

		var req = {
			method: 'POST',
			url: '/site-config?uuid='+site_uuid,
			headers: {
				'Content-Type': 'application/json'
			},
			data: { dataObj }
		}

		$http(req)
		.then(function successCallback(response) {
			console.log("POSTed");
			console.log(response);
      $scope.saveConfigStatus = 2;
			// this callback will be called asynchronously
			// when the response is available
		}, function errorCallback(response) {
			console.log("POSTing ERROR!");
			console.log(response);
      $scope.saveConfigStatus = 3;
			// called asynchronously if an error occurs
			// or server returns response with an error status.
		});

	}

	$scope.deleteSite = function() {
		console.log("Received a request to delete a serena site: " + JSON.stringify($scope.siteConfig));
    $scope.deleteSiteStatus = 1;

		var req = {
			method: 'POST',
			url: '/site-delete?uuid='+site_uuid,
			headers: {
				'Content-Type': 'application/json'
			}
		}

		$http(req)
		.then(function successCallback(response) {
			console.log("POSTed");
			console.log(response);
      $scope.deleteSiteStatus = 2;
      $scope.saveConfigStatus = 9;
			// this callback will be called asynchronously
			// when the response is available
		}, function errorCallback(response) {
			console.log("POSTing ERROR!");
			console.log(response);
      $scope.deleteSiteStatus = 3;
			// called asynchronously if an error occurs
			// or server returns response with an error status.
		});

	}


// person actions
	$scope.showPerson = function(person,index) {
		console.log("Got to showPerson: "+JSON.stringify(person)+ "["+index+"]");
		$scope.selectedPerson = person;
		$scope.lastPersonClicked = index;
	}

	$scope.statusChanged = function(index) {
		console.log("Got to statusChanged: "+JSON.stringify(index));
		console.log("Contacts: "+JSON.stringify($scope.siteConfig.contacts));
	}

	$scope.addContact = function(index) {
		var conlength = Object.keys($scope.siteConfig.contacts).length;
		console.log("We currently have " + conlength + " contacts defined");
		if ( conlength == 6 ) { alert("Sorry, we only allow 6 contacts at the moment!"); } else {
			$scope.siteConfig.contacts[(conlength+1)] = new Object;
			$scope.siteConfig.contacts[(conlength+1)].name = 'New User ' + (conlength+1);
		}
	}

	$scope.removeContact = function() {
		console.log("Would remove the person at index position: " + $scope.lastPersonClicked);
		delete $scope.siteConfig.contacts[($scope.lastPersonClicked+1)];
		//$scope.siteConfig.contacts[($scope.lastPersonClicked+1)] = undefined;
		// NEED TO WORK THIS OUT... the REDIS data is still there, so removing from the object
		// doesn't remove it from REDIS, since we're only updating... FIX May 23rd 2017
		console.log(JSON.stringify($scope.siteConfig.contacts));
	}

// notification groups actions
	$scope.showGroup = function(group,index) {
		console.log("Got to showGroup: "+JSON.stringify(group)+ "["+index+"]");
		$scope.selectedGroup = group;
		$scope.lastGroupClicked.index = index;
		$scope.lastGroupClicked.name = group;
	}

	$scope.statusChangedG = function(index) {
		console.log("Got to statusChangedG: "+JSON.stringify(index));
		console.log("groups: "+JSON.stringify($scope.siteConfig.notificationGroups));
	}

	$scope.addGroup = function(index) {
		var conlength = Object.keys($scope.siteConfig.notificationGroups).length+1;
		console.log("We currently have " + conlength + " notification groups defined");
		if ( conlength >= 11 ) { alert("Sorry, we only allow 10 groups at the moment!"); } else {
			$scope.siteConfig.notificationGroups[(conlength+1)] = new Object;
			$scope.siteConfig.notificationGroups[(conlength+1)].index = conlength;
			$scope.siteConfig.notificationGroups[(conlength+1)].name = 'New Group ' + (conlength);
		}
	}

	$scope.changedGroup = function(index) {
		console.log("Got to changedGroup:" + index);
	}

	$scope.updateGroupName = function(last_clicked) {
		console.log("Got to updateGroupName:" + last_clicked.name + ":"+ $scope.selectedGroupName);
		var tmp = [];
			for (var gName in $scope.siteConfig.notificationGroups) {
				console.log("gName: " + gName);
			}
//	        var aname = qca.rows[varI].key;
//		if ( aname === $scope.previous ) { aname = 'Me'; $scope.ready = 1; }

		
		$scope.siteConfig.notificationGroups[last_clicked.name] = $scope.selectedGroupName;
		$scope.lastGroupClicked.name = last_clicked.name;
	}

	$scope.removeGroup = function() {
		var ngID = $scope.lastGroupClicked.index+1;
		console.log("Would remove the group at index position: " + JSON.stringify($scope.siteConfig.notificationGroups[ngID]));
		delete $scope.siteConfig.notificationGroups[ngID];
		//$scope.siteConfig.contacts[($scope.lastPersonClicked+1)] = undefined;
		// NEED TO WORK THIS OUT... the REDIS data is still there, so removing from the object
		// doesn't remove it from REDIS, since we're only updating... FIX May 23rd 2017
		console.log(JSON.stringify($scope.siteConfig.notificationGroups));
	}

// Trigger actions
	$scope.showTrigger = function(key,trigger,index) {
		console.log("Got to showTrigger: ["+key+"] "+JSON.stringify(trigger)+ "["+index+"]");
    // if the trigger does not have a secondsHeld value then use the default duration
    if (typeof(trigger.secondsHeld) == 'undefined') {
      trigger['secondsHeld'] = $scope.siteConfig.alert.secondsHeld;
    }
    if (typeof(trigger.icon) == 'undefined') {
      trigger['icon'] = 'fa-wrench';
    }
		$scope.selectedTrigger = trigger;
		$scope.lastTriggerClicked = trigger;
    $scope.lastTriggerClicked.index = index;
    $scope.lastTriggerClicked.key = key;
	}

	$scope.statusChangedT = function(index) {
		console.log("Got to statusChangedT: "+JSON.stringify(index));
		console.log("triggers: "+JSON.stringify($scope.siteConfig.triggers));
	}

	$scope.addTrigger = function(index) {
    // request new UUID 
    
   	var req = {
			method: 'POST',
			url: '/uuid',
			headers: {
				'Content-Type': 'application/json'
		},
			data: { uuid: site_uuid, utype: 'trigger' }
		};


		$http(req)
		.then(function successCallback(response) {
			console.log("UUID requested OK");
			console.log(response);
		var conlength = Object.keys($scope.siteConfig.triggers).length;
		console.log("We currently have " + conlength + " notification groups defined");
		if ( conlength >= 11 ) { alert("Sorry, we only allow 10 Triggers at the moment!"); } else {
			$scope.siteConfig.triggers[response.data.uuid] = new Object;
			$scope.siteConfig.triggers[response.data.uuid].index = conlength;
			$scope.siteConfig.triggers[response.data.uuid].name = 'New Trigger ' + (conlength+1);
		}
			// this callback will be called asynchronously
			// when the response is available
		}, function errorCallback(response) {
			console.log("UUID request ERROR!");
			console.log(response);
			// called asynchronously if an error occurs
			// or server returns response with an error status.
		});
		
	}

	$scope.changedTrigger = function(index) {
		console.log("Got to changedTrigger:" + index);
	}

	$scope.updateTriggerName = function(last_clicked) {
		console.log("Got to updateTriggerName:" + last_clicked.name + ":"+ $scope.selectedTriggerName);
		var tmp = [];
			for (var tName in $scope.siteConfig.triggers) {
				console.log("tName: " + tName);
			}
		
//		$scope.siteConfig.triggers[last_clicked.name] = $scope.selectedtriggerName;
//		$scope.lastTriggerClicked = last_clicked.name;
	}

	$scope.removeTrigger = function() {
		var tID = $scope.lastTriggerClicked;
    console.log(JSON.stringify(tID));
		console.log("Would remove the Trigger ["+tID.key+"] at index position: " + tID.index);
		delete $scope.siteConfig.triggers[tID.key];
		//$scope.siteConfig.contacts[($scope.lastPersonClicked+1)] = undefined;
		// NEED TO WORK THIS OUT... the REDIS data is still there, so removing from the object
		// doesn't remove it from REDIS, since we're only updating... FIX May 23rd 2017
		console.log(JSON.stringify($scope.siteConfig.triggers));
	}


}]);


