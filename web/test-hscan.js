const express = require('express'),
	exphbs = require('express-handlebars'),
	path = require('path'),
	bodyParser = require('body-parser'),
	methodOverride = require('method-override'),
	helmet = require('helmet'),
	redis = require('redis'),
	config = require('./config.js'),
	uuidV4 = require('uuid/v4');

// Create Redis client
let client = redis.createClient(config.redis_port, config.redis_host), multi;

client.auth(config.redis_auth, function (err) {
	if (err) {
		throw err;
	}
});

/*
//No Longer need this custom scan function since I got igetall working
function scan(pattern, callback) {
	client.hscan(pattern, 0, (e,r) => {
		var ian = new Object;
		Object.keys(r[1]).forEach(function(key, i) {
			if ( i %2 === 0 ) { //index is even
				ian[r[1][i]] = new Object;
			} else {
				ian[r[1][i-1]] = r[1][i];
			}
		});
		callback(ian);
	});
}
*/

function irange(key, callback) {
	client.lrange(key, 0, -1, (e,r) => {
		callback(r);
	});
}

function igetall(key, callback) {
	client.hgetall(key, (e,r) => {
		callback(r);
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


client.on('connect', () => {
	//console.log("Connected to Redis")

	// custom attempt to perform a similar hgetall	
	// did this to work out the callback function
	// this is just an example - wouldn't use this in prod
	//scan('65ae194f-0336-4b8f-972d-6803ea88f2f3:config:contacts:1', function(obj) {
	//		console.log("Hello: obj=" + JSON.stringify(obj));
	//});

	// New function to return everything we need - SWEET - thanks to callbacks
	ikeys('65ae194f-0336-4b8f-972d-6803ea88f2f3:config:*', (key,type,data) => {
		console.log("key: [" + key + "]\nvalue: " + JSON.stringify(data));
	});

	// This is preferred rather than my custom scan function
	// look for whatever records we have that match a pattern and return all the data
});
