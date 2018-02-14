const express = require('express'),
	exphbs = require('express-handlebars'),
	path = require('path'),
	bodyParser = require('body-parser'),
	methodOverride = require('method-override'),
	helmet = require('helmet'),
	redis = require('redis'),
	config = require('./config.js'),
	moniker = require('moniker'),
	uuidV4 = require('uuid/v4');

// Create Redis client
let client = redis.createClient(config.local_redis_port, config.local_redis_host), multi;

// not authing on localhost
//client.auth(config.redis_auth, function (err) {
//	if (err) {
//		throw err;
//	}
//});

// Connect to Redis
client.on('connect', () => {
			console.log("Connected to Redis")
});

// Module middleware:

// Init app
const app = express();

// Put on our helmet!
app.use(helmet());

// Tell the app to use the public directory for static content
app.use(express.static(path.join(__dirname, 'public')));

// Trying some handlebar helpers
const hbs = exphbs.create({
	defaultLayout:'main',
	helpers: {
		// KEEP IN MIND THESE ARE SUPPOSED TO RETURN HTML!
		foo: function () { return 'FOO!'; },
		bar: function () { return 'BAR!'; },
		option: function(value, label, selectedValue) {
			var selectedProperty = value == selectedValue ? 'selected="selected"' : '';
			//return new exphbs.SafeString('<option value="' + value + '"' +  selectedProperty + '>' + label + "</option>");
			return '<option value="' + value + '" ' +  selectedProperty + '>' + label + "</option>";
		}
	}
});


// View engine
//app.engine('handlebars', exphbs({defaultLayout:'main'}));
app.engine('handlebars', hbs.engine);
app.set('view engine', 'handlebars');

// body-parser
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended:false}));

// method-override
app.use(methodOverride('_method'));
page = {};

// Routes:

// Search page
app.get('/', function(req, res, next){
	res.render('welcome', {
		page: {home: 'Yes'}
	});
});

// Search processing
app.post('/user/search', function(req, res, next){
	let id = req.body.id;
	
	client.hgetall(id, (err, obj) => {
		if (! obj) {
			res.render('searchusers', {
				error: 'User does not exist'
			});
		} else {
			obj.id = id;
			res.render('details', {
				user: obj
			})
		}
	});	
});

// Display ALL Sites search page
app.get('/sites', function(req, res, next){

		var db_array = new Array();

		// extract uuids (which includes the nice site name)
		// so the user can select a site and we know which 
		// site we can point to while also maintaining 
		// some level of security that people can't
		// guess the uuid of each site very easily
		// unless they can access this page!!!

		client.hgetall("uuids",function(err, reply){
			//console.log(reply);
			if ( reply ) {
				var items = [];
				for (i in reply) {
					var line = {db_uuid: i, db_id: db_array.length, db_name: reply[i]};
					db_array.push(line);
				}
				res.render('sites', {
					serenaDBs: db_array,
					page: {sites: 'Yes'}
				});
			} else {
				// used to send to the error page, but show a new option for initial site creation
				//res.render('error-contact', {
				//	error: 'Unable to extract sites from the database!',
				//	page: {contact: 'Yes'}
				//});
				res.render('sites', {
					serenaDBs: [],
					page: {sites: 'Yes'}
				});
			}    
		});

});


// JSON SETTER
app.post('/site-config', function(req, res, next){
    let site_id = req.query.uuid;
    let json_to_parse = req.body.dataObj;
    let parsed_json = JSON.parse(json_to_parse);
    // add _test so we don't mess with the dummy data
    console.log("User requested to update the configuration for the ["+site_id+"] site");
    //console.log(parsed_json.sensorInputs);

    //console.log("Saving to: " + site_id+ " and trying to save this: " + parsed_json.sensorInputs);
    client.hmset(site_id+":config:sensors:input", parsed_json.sensorInputs, function(e1,r1) {
      if (e1) console.log("Problem with e1: " + e1);
      //console.log("sensor inputs inserted");
      client.hmset(site_id+":config:sensors:output", parsed_json.sensorOutputs, function(e1,r1) {
        if (e1) console.log("Problem with e1: " + e1);
        //console.log("sensor outputs inserted");
        client.hmset(site_id+":config:siteInfo", parsed_json.siteInfo, function(e1,r1) {
          if (e1) console.log("Problem with e1: " + e1);
        client.hmset(site_id+":config:startup", parsed_json.startup, function(e1a,r1a) {
          if (e1a) console.log("Problem with e1a: " + e1a);
          //console.log("siteInfo inserted");
          client.hmset(site_id+":config:earlyWarning", parsed_json.earlyWarning, function(e1,r1) {
        client.hmset(site_id+":config:device", "update_required", "1", function(e1z,r1z) {
          if (e1z) console.log("Problem with e1a: " + e1z);
          //console.log("config update inserted");
            if (e1) console.log("Problem with e1: " + e1);
            //console.log("earlyWarning inserted");
            client.hmset(site_id+":config:alert", parsed_json.alert, function(e1,r1) {
              if (e1) console.log("Problem with e1: " + e1);
              //console.log("alert inserted");

              Object.keys(parsed_json.triggers).forEach(function(key, i) {
                client.hmset(site_id+":config:triggers:"+key, parsed_json.triggers[key], function(e1,r1) {
                  if (e1) console.log("Problem with e1: " + e1);
                  console.log("triggers [" + key + "] inserted on: "+site_id);
                  });
                });

              // we know we only support 6 contacts so loop through them, rather than looping through what was sent.
              fix_contact_gaps = new Array;
              [1,2,3,4,5,6].forEach(function(i) {
                client.del(site_id+":config:contacts:"+i, function(e1,r1) {
                  console.log("deleted: "+site_id+":config:contacts:"+i);
                  if ( typeof parsed_json.contacts[i] != 'undefined' ) {
                  if ( "name" in parsed_json.contacts[i] ) {
                  //fix_contact_gaps.push(i); FIX THIS MAY 23 2017
                  client.hmset(site_id+":config:contacts:"+i, parsed_json.contacts[i], function(e2,r2) { 
                    if (e2) console.log("Problem with e2: " + e2);
                    console.log("contacts [" + i + "] inserted on: "+site_id);
                    });
                  }
                  }
                  });
                });
              //Object.keys(parsed_json.contacts).forEach(function(key, i) {
              //    client.del(site_id+":config:contacts:"+key, function(e1,r1) {
              //	console.log("deleted: "+site_id+":config:contacts:"+key);
              //	client.hmset(site_id+":config:contacts:"+key, parsed_json.contacts[key], function(e2,r2) {
              //		if (e2) console.log("Problem with e2: " + e2);
              //		console.log("contacts [" + key + "] inserted on: "+site_id);
              //	});
              //    });
              //});

              // NEW May 24th 2017 notificationGroups
              fix_contact_gaps = new Array;
              [1,2,3,4,5,6,7,8,9,10].forEach(function(i) {
                  client.del(site_id+":config:notificationGroups:"+i, function(e1,r1) {
                    console.log("deleted: "+site_id+":notificationGroups:"+i);
                    if ( typeof parsed_json.notificationGroups[i] != 'undefined' ) {
                    if ( "name" in parsed_json.notificationGroups[i] ) {
                    //fix_contact_gaps.push(i); FIX THIS MAY 23 2017
                    client.hmset(site_id+":config:notificationGroups:"+i, parsed_json.notificationGroups[i], function(e2,r2) { 
                      if (e2) console.log("Problem with e2: " + e2);
                      console.log("notificationGroups [" + i + "] inserted on: "+site_id);
                      });
                    }
                    }
                    });
                  });

              //Object.keys(parsed_json.notificationGroups).forEach(function(key, i) {
              //	//console.log("Deleting notificationGroup [" + key + "]  on: "+site_id);
              //	client.del(site_id+":config:notificationGroups:"+key, function(e1,r1) {
              //		//console.log("Deleted, pushing new content");
              //		client.lpush(site_id+":config:notificationGroups:"+key, parsed_json.notificationGroups[key], function(e2,r2) {
              //			if (e2) console.log("Problem with e1: " + e2);
              //		});
              //	});
              //});

              client.hget(site_id+":config:siteInfo", "courtInitials", function(e1,r1) {
                  //console.log("Setting Site Initials to ["+r1+"]");
                  client.hset("uuids", site_id, r1, function(e2,r2) {
                    //res.send(JSON.stringify({ status: "OK"}, null, 3));
                    //res.redirect('/sites');
                    if (e2) {
                    console.log("Problem with e2: " + e2);
                    res.json({ message: "ERR"});
                    } else {
                    res.json({ message: "OK"});
                    }
                    });
                  });
            });
          });
          });
        });
      });
      });
    });
});


// DELETE SITE 
app.post('/site-delete', function(req, res, next){
    var passedSiteUUID = req.query.uuid;
    if (passedSiteUUID) {
    console.log("/site-delete [uuid:"+passedSiteUUID+"]");

    multi = client.multi();
    // extract input sensors configuration (hash) - count of 2000 just to make sure we get everything!
    client.scan(0, "MATCH", passedSiteUUID+":*", "Count", "2000", function(e1,r1) {
      console.log(r1);
      if (e1) {
      res.setHeader('Content-Type', 'application/json');
      res.status(500).send({ status: "ERROR, unable to delete site!" });
      return console.log(e1);
      } else {
      for (key in r1[1]){
      // add the keys to the multi
      multi.del(r1[1][key]);
      //console.log("will delete key: ["+key+"] "+r1[1][key]);
      }
      if ( (r1[1].length-1) == key ) {
      console.log(r1[1].length-1+" = " + key);
      // all keys have been deleted
      // remove the site from the uuid hash

      multi.hdel('uuids', passedSiteUUID);
      // execute multi
      multi.exec(function (err, replies) {
        if ( err ) {
        res.setHeader('Content-Type', 'application/json');
        res.status(500).send({ status: "ERROR, unable to delete site! "+err });
        } else {
        res.setHeader('Content-Type', 'application/json');
        res.send(JSON.stringify({ status: "OK", process: "Deleted Site", output: replies }, null, 3));
        }
        });
      }
      }
    });
    } else {
      res.setHeader('Content-Type', 'application/json');
      res.status(500).send({ status: "ERROR, unable to delete site!" });
    }
});

// UUID POST Request 
app.post('/uuid', function(req, res, next){
    var passedSiteUUID = req.body.uuid;
    var uuidType = req.body.utype;
    if (passedSiteUUID && uuidType) {
    console.log("/requesting type ["+uuidType+"] for site [uuid:"+passedSiteUUID+"]");

    var uuid = uuidV4();

    if (uuid) {
      // add uuid to the correct redis record
      if ( uuidType == 'trigger' ) {
        client.rpush(passedSiteUUID+":config:triggerSet", uuid, function (e1,r1) {
          if (e1) {
            console.log(e1);
            res.setHeader('Content-Type', 'application/json');
            res.status(500).send({ status: "ERROR, unable to locate uuid!" });
          }
        });
      }
      res.setHeader('Content-Type', 'application/json');
      res.send(JSON.stringify({ status: "OK", uuid: uuid }, null, 3));
    } else {
      res.setHeader('Content-Type', 'application/json');
      res.status(500).send({ status: "ERROR, unable to locate uuid!" });
    }
   } else {
      res.setHeader('Content-Type', 'application/json');
      res.status(500).send({ status: "ERROR, unable to locate uuid site!" });
   }
});



// NEW JSON GETTER - faster, leaner, meaner - using scan so it should be lightning fast
app.get('/site-config2', function(req,res,next){
    var passedSiteUUID = req.query.uuid;
    var items = new Object;
    items['notificationGroups'] = new Object();
    items['triggers'] = new Object();
    items['contacts'] = new Object();
    client.scan(0, "MATCH", passedSiteUUID+":*", "Count", "2000", function(e,r) {
      if ( r[1].length > 1 ) {
        for ( key in r[1] ) { 
          //console.log("Working on: "+r[1][key]); 

            igetall2(key, r[1][key], function(ps, ky, object) {
              //console.log("pos: ["+ps+"] key: ["+ky+"] object = " +JSON.stringify(object));

              // object contains all the keys and values for the redis hash
              // let's do something with them here

              var elements = ky.split(':');
              // elements[0] is always the passedSiteUUID
              // elements[1] is always either config or sensor
              if ( elements[1] == 'config' ) {
                if ( elements[2] == 'siteInfo' ) {
                  items['siteInfo'] = object;
                } else if ( elements[2] == 'startup' ) {
                  if ( object.sms ) { object.sms = (object.sms == "true"); }
                  if ( object.email ) { object.email = (object.email == "true"); }
                  items['startup'] = object;
                } else if ( elements[2] == 'sensors' ) {
                  if ( elements[3] == 'input' ) {
                    items['sensorInputs'] = object;
                  } else if ( elements[3] == 'output' ) {
                    items['sensorOutputs'] = object;
                  } else if ( elements[3] == 'mapping' ) {
                    items['sensorMappings'] = object;
                  }
                } else if ( elements[2] == 'earlyWarning' ) {
                  items['earlyWarning'] = object;
                } else if ( elements[2] == 'device' ) {
                  items['device'] = object;
                } else if ( elements[2] == 'alert' ) {
                  items['alert'] = object;
                } else if ( elements[2] == 'redis' ) {
                  items['redis'] = object;
                } else if ( elements[2] == 'notificationGroups' ) {
                  items['notificationGroups'][elements[3]] = object;
                } else if ( elements[2] == 'triggers' ) {
                  if ( object.buzzerSolidAlert ) { object.buzzerSolidAlert = (object.buzzerSolidAlert == "true"); } else { object.buzzerSolidAlert = (object.buzzerSolidAlert == "false"); }
                  if ( object.buzzerChirpAlert ) { object.buzzerChirpAlert = (object.buzzerChirpAlert == "true"); } else { object.buzzerChirpAlert = (object.buzzerChirpAlert == "false"); }
                  if ( object.responseRequired ) { object.responseRequired = (object.responseRequired == "true"); } else { object.responseRequired = (object.responseRequired == "false"); }
                  items['triggers'][elements[3]] = object;
                } else if ( elements[2] == 'contacts' ) {
                  if ( object.allowAdmin ) { object.allowAdmin = (object.allowAdmin == "true"); }
                  if ( object.grantStatus ) { object.grantStatus = (object.grantStatus == "true"); }
                  items['contacts'][elements[3]] = object;
                }
              }

              // all done, so let's send the JSON out
              if ( key == ps ) {
                                              res.setHeader('Content-Type', 'application/json');
                                              res.send(JSON.stringify({ status: "OK", siteConfig: items }, null, 3));
              }
            });
        }
                                          
      } else {
        res.setHeader('Content-Type', 'application/json');
        res.status(500).send({ status: "ERROR, unable to extract site configuration!"});
        return console.log(e);
      }
    });
});


// GET Sensor values and return in JSON format
app.get('/site-sensor-values', function(req,res,next){
    var passedSiteUUID = req.query.uuid;
    var collection = new Array;

    client.scan(0, "MATCH", passedSiteUUID+":lastAvgValue:*", "Count", "2000", function(e,r) {
      if ( r[1].length > 1 ) {
        for ( key in r[1] ) { 
          //console.log("Working on: "+r[1][key]); 

            igetall2(key, r[1][key], function(ps, ky, object) {
              //console.log("pos: ["+ps+"] key: ["+ky+"] object = " +JSON.stringify(object));
              // object contains all the keys and values for the redis hash
              // let's do something with them here

              var elements = ky.split(':');
              // elements[0] is always the passedSiteUUID
              // elements[1] is always either config or sensor
              if ( elements[1] == 'lastAvgValue' ) {
		// elements[2] is the trigger key
		object.bgColor = 'panel-green';
		if ( object.triggerClause == 'matchvalue' ) {
			if ( object.avgValue == object.triggerValue ) {
				object.bgColor = 'panel-red';
			}
		}
		if ( object.triggerClause == 'max' ) {
			if ( object.avgValue > object.triggerValue ) {
				object.bgColor = 'panel-red'; 
			}
		}
		if ( object.triggerClause == 'min' ) {
			if ( object.avgValue < object.triggerValue ) {
				object.bgColor = 'panel-red'; 
			}
		}
		// Need to add the trigger ID so we can use it in the stats graph
		object.triggerId = elements[2];
                object.epoch = parseInt(object.epoch);
		collection.push(object);
              }

              // all done, so let's send the JSON out
              if ( key == ps ) {
			res.setHeader('Content-Type', 'application/json');
			res.setHeader('Access-Control-Allow-Origin', '*');
			res.send(JSON.stringify({ status: "OK", sensorValues: collection }, null, 3));
              }
            });
        }
                                          
      } else {
        res.setHeader('Content-Type', 'application/json');
        res.status(500).send({ status: "ERROR, unable to extract site sensor values!"});
        return console.log(e);
      }
    });
});


// GET Historical Sensor values and return in JSON format (for use in graph)
app.get('/site-historical-sensor-values', function(req,res,next){
    var passedSiteUUID = req.query.uuid;
    var triggerID = req.query.tid;
    // set the default amount of values to go back to 50 if the back value isn't present in the URL
    var howFarToGoBack = (typeof req.query.back !== 'undefined') ? req.query.back - (req.query.back *2) : -50;

            client.zrange(passedSiteUUID +":histAvgValue:" + triggerID, howFarToGoBack, -1, function(err, data) {
		if ( typeof data[0] !== 'undefined' ) {
			res.setHeader('Content-Type', 'application/json');
			res.setHeader('Access-Control-Allow-Origin', '*');
			res.send(JSON.stringify({ status: "OK", historicSensorValues: data }, null, 3));
		} else {
			res.setHeader('Content-Type', 'application/json');
			res.status(500).send({ status: "ERROR, unable to extract site sensor values!"});
		}
	});
});


// GET Last Image Captures and return in JSON format (for use in graph)
app.get('/site-image-captures', function(req,res,next){
    var passedSiteUUID = req.query.uuid;
    // set the default amount of values to go back to 5 if the back value isn't present in the URL
    var howFarToGoBack = (typeof req.query.back !== 'undefined') ? req.query.back - (req.query.back *2) : -5;

            client.zrange(passedSiteUUID +":capturedImages", howFarToGoBack, -1, function(err, data) {
		if ( typeof data[0] !== 'undefined' ) {
			res.setHeader('Content-Type', 'application/json');
			res.setHeader('Access-Control-Allow-Origin', '*');
			res.send(JSON.stringify({ status: "OK", capturedImages: data }, null, 3));
		} else {
			res.setHeader('Content-Type', 'application/json');
			res.status(500).send({ status: "ERROR, unable to extract values!"});
		}
	});
});


	

// Display Individual Site page
app.get('/site', function(req, res, next){
	var passedSiteUUID = req.query.uuid;
	// should probably do something to protect TODO

	if (passedSiteUUID) {
		// Is this a valid UUID?
		client.exists(passedSiteUUID+':config:siteInfo', function(er,re) {
			if ( re === 1 ) {
				res.cookie('serenaSiteUUID', passedSiteUUID, {
					path: '/',
					maxAge: 9000000,
					secure: false,
					httpOnly: false
				});
				res.render('site', {
					page: {sites: 'Yes', tab:{dashboard: 'Yes'}}
				});
			} else {
				res.render('error-contact', {
					error: 'Unable to extract sites from the database!',
					page: {contact: 'Yes'}
				});
			}
		});
	}
});


		


//  Process Site Selection
app.post('/sites/search', function(req, res, next){
	let site_id = req.body.selectSerenaSite;
	console.log("User picked the ["+site_id+"] site");
	//console.log(req.body);

	if (site_id == "NEW") {

// rather than creating the site at this point, just present the inputs
// to allow them up add more information before we just go ahead 
// and assign a new UUID and get thing already going!
// maybe they might change their mind 

// when a user selects the 'NEW SITE' option we need to assign two UUID's for usage.
		
		console.log("Creating a new site...");
		site_uuid = uuidV4();
		app_uuid = uuidV4();
    site_name = moniker.choose();
		console.log("Creating a new site called: ["+site_name+"]");
		console.log("Using the following UUIDs:\n SITE:["+site_uuid+"]\n APP:["+app_uuid+"]");
//    HMSET "65ae194f-0336-4b8f-972d-6803ea88f2f3:config:siteInfo" "courtName" "Brick and Mortor - Utah" "courtInitials" "TRB" "pointOfContact" "2" "app_uuid" "a3ce20d1-8dc2-4c64-8a8e-2f710b85bf9a"

// Tell Redis the new site values and setup a skeleton site
		client.hset("uuids", site_uuid, site_name, function (e,r) {
		  if (e) return console.log(e);

      client.hmset(site_uuid+":config:siteInfo",
        "courtName", site_name,
        "courtInitials", site_name,
        "pointOfContact", "1",
        "hostname", "serena.local",
        "parentHostname", "serena.local",
        "app_uuid", app_uuid,
	"site_uuid", site_uuid, function (e1,r1){
          if (e1) return console.log(e1);

      client.hmset(site_uuid+":config:startup",
        "sms", "false",
        "email", "false",
        "notificationGroup", "serenaStart", function (e1a, r1a) {
          if (e1a) return console.log(e1a);

            client.hmset(site_uuid+":config:contacts:1",
              "name", "John Smyth",
              "textNumber", "+18015555555",
              "grantStatus", "true",
              "allowAdmin", "true",
              "email", "your_email_here@example.com",
              "officeNumber", "+18015555555", function (e2,r2){
                if (e2) return console.log(e2);

                  client.hmset(site_uuid+":config:sensors:input",
                    "dht", "4",
                    "button", "2",
                    "dial", "0",
                    "power", "21",
                    "water", "8",
                    "pir", "3", function (e3,r3){
                      if (e3) return console.log(e3);

                        client.hmset(site_uuid+":config:sensors:output",
                          "lcd", "1",
                          "gLed", "5",
                          "rLed", "6",
                          "buzzer", "7", function (e4,r4){
                            if (e4) return console.log(e4);

                              client.hmset(site_uuid+":config:sensors:mapping",
                                "dht-temperature", "temperature",
                                "dht-humidity", "humidity",
                                "power", "power",
                                "water", "water",
                                "pir", "motion",
                                "cpuTemp", "serenaTemp",
                                "ping", "network", function (e5,r5){
                                  if (e5) return console.log(e5);

                                    client.hmset(site_uuid+":config:redis",
                                      "sensor_path", site_uuid+":sensors", function (e6,r6){
                                        if (e6) return console.log(e6);

                                          client.hmset(site_uuid+":config:earlyWarning",
                                            "secondsBeforePromotion", "60",
                                            "secondsMuteHeld", "600", function (e7,r7){
                                              if (e7) return console.log(e7);

                                                client.hmset(site_uuid+":config:alert",
                                                  "secondsHeld", "1200",
                                                  "secondsForContactResponse", "120",
                                                  "secondsNextContactCascade", "600",
                                                  "secondsBetweenThresholdCheck", "60",
                                                  "secondsBetweenMotionCapture", "30", function (e8,r8){
                                                    if (e8) return console.log(e8);

                                                      trigger_uuid = uuidV4();

                                                      client.hmset(site_uuid+":config:triggers:"+trigger_uuid,
                                                        "name", "tempOver",
                                                        "max", "28",
                                                        "notificationGroup", "itStaff",
                                                        "buzzerSolidAlert", "true",
                                                        "audibleAlert", "none",
                                                        //"sensor", "dht-temperature",
                                                        "minCycles", "10",
                                                        "notificationStyle", "all",
                                                        "responseRequired", "true",
                                                  	"secondsHeld", "600",
                                                  	"icon", "fa-wrench",
                                                        "redis_key", "temperature", function (e9,r9){
                                                          if (e9) return console.log(e9);

                                                            client.RPUSH(site_uuid+":config:triggerSet", trigger_uuid, function (e10,r10) {
                                                                if (e10) return console.log(e10);

                                                                  client.hmset(site_uuid+":config:notificationGroups:1",
                                                                    "name", "itStaff",
                                                                    "contacts", "1",
                                                                    "active", "true", function (e11,r11){
                                                                      if (e11) return console.log(e11);

                                                                  client.hmset(site_uuid+":config:notificationGroups:2",
                                                                    "name", "serenaStart",
                                                                    "contacts", "1",
                                                                    "active", "true", function (e12,r12){
                                                                      if (e12) return console.log(e12);

	                                                                    res.redirect('/site?uuid=' + site_uuid +'&section=siteInfo');

                                                                  });

                                                                  });
                                                                       
                                                            });
                                                      });
                                                });
                                        });
                                });
                          });
          });
        });
      });
    });
    });
   });

	} else {
	  res.redirect('/site?uuid=' + site_id +'&section=siteInfo');
	}
});


// Display Status page
app.get('/status', function(req, res, next){
	var passedSiteUUID = req.query.uuid;
	res.render('status', {
		page: {status: 'Yes'}
	});
});


// Display Support page
app.get('/support', function(req, res, next){
	var passedSiteUUID = req.query.uuid;
	res.render('support', {
		page: {contact: 'Yes'}
	});
});


// Add User page
app.get('/user/add', function(req, res, next){
	res.render('adduser', {
		page: {addUser: 'Yes'}
	});
});


// Add User processing
app.post('/user/add', function(req, res, next){
	let id = req.body.id;
	let first_name = req.body.first_name;
	let last_name = req.body.last_name;
	let email = req.body.email;
	let phone = req.body.phone;
	
	client.hmset(id, [
		'first_name', first_name,
		'last_name', last_name,
		'email', email,
		'phone', phone
	], function (err, reply) {
		if (err) {
			console.log(err);
		}
		console.log(reply);
		res.redirect('/');
	});
});



// Delete user
app.delete('/user/delete/:id', function(req, res, next) {
	client.del(req.params.id);
	res.redirect('/');
});


// Functions - routine things we do

function igetall(key, callback) {
        client.hgetall(key, (e,r) => {
                callback(r);
        });
}

function igetall2(pos, key, callback) {
  client.hgetall(key, (e,r) => {
    callback(pos,key, r);
  });
}

function ikeys(pattern, callback) {
        client.keys(pattern, (e,r) => {
                Object.keys(r).forEach(function(key, i) {
                        igetall(r[key], function(r1) {
                                if ( typeof(r1) != 'undefined' ) {
                                        callback(r[key], 'o', r1);
                                } else {
                                        irange(r[key], function(r2) {
                                                callback(r[key], 'a', r2);
                                        });
                                }
                        });
                });
        });
}




// Set up listener on a port
app.listen(config.web_port, function(){
	console.log('Server started on port '+config.web_port);
});
