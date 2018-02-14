This will perform the loading of testing data into Redis, database #2

cat testing_data.txt | redis-cli -h 127.0.0.1 -p 9080 -a HelloWorldOfRedis -n 2
