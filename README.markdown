# Odin
Odin is a system to run arbitrary programs on your cluster.

Currently there is no scheduler.

It is a proof of concept at the moment and is terribly inefficient and threaded
badly.

Built on:
 * [ZooKeeper](http://zookeeper.apache.org/)
 * [supervisord](http://supervisord.org)
 * [Protocol Buffers](http://code.google.com/apis/protocolbuffers)
 * [supervisor_twiddler](https://github.com/mnaberez/supervisor_twiddler)


## Terms:
 * Runnable: a command and configuration to run a program on a single machine
   which will be monitored.
 * Task: A single instance of a job. Contains a single runnable, information for 
   where to get program and files.
 * Job: A set of tasks (each with multiple instances). A user creates a Job to be
   run somewhere on the cluster.
 * Machine: A computer where many tasks will run. Runs a supervisord instance.
   It has an IP.
 * Politician (Need a better name): A server that may become the leader of the
   cluster. A politician schedules jobs on the cluster and accepts Jobs to be
   added to the cluster. Only one politician is in charge, they are the Leader.
   Leaders are elected through a ZooKeeper based algorithm.