# Odin
Odin is a system to run arbitrary programs on your cluster.

Currently there is no scheduler.

It is a proof of concept at the moment and is terribly inefficient and threaded
badly.

Build on:
	* [ZooKeeper](http://zookeeper.apache.org/)
	* [supervisord](http://supervisord.org)
	* [Protocol Buffers](http://code.google.com/apis/protocolbuffers)
	* [supervisor_twiddler](https://github.com/mnaberez/supervisor_twiddler)