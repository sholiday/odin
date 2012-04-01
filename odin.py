#!/usr/bin/env python
# encoding: utf-8
"""
Odin.py

Created by Stephen Holiday on 2012-03-27.
Copyright (c) 2012 Stephen Holiday. All rights reserved.

Attempts to follow the Google Python Style Guide:
http://google-styleguide.googlecode.com/svn/trunk/pyguide.html

Not because I think it's the best, but because it's a standard.
"""

import json
import logging
import odin_pb2
import os
import signal
import sys
import threading
import time
import xmlrpclib
import zookeeper

logger = logging.getLogger() 

ZOO_OPEN_ACL_UNSAFE = {"perms":0x1f, "scheme":"world", "id" :"anyone"};

def path_join(a, b):
    return a + '/' + b
    
def path_pop(a):
    return a.split('/').pop()

def path_cell(a):
    parts = a.split('/')
    return '/' + parts[1] + '/' + parts[2]

class Odin():
    '''
        A machine in the cell exists via a node like:
            /odin/cell/machines/m-??????
        These are ephemeral. If we are creating a node, we will use create
        sequence.
            
        A job exists in the cell via a node like:
            /odin/cell/jobs/j-?????
        Maybe not ephemeral, but deleted when completed. Create sequence.
        
        A task that is to be run on a machine is at:
            /odin/cell/tasks/m-????/task-????
        Where m-??? is the machine and the task is sequential. The contents is
        in the job. Any new tasks under there will start a job on the machine.
    
    '''
    _cell = None
    _cell_default = '/odin/test'
    _z = None
    def __init__(self, zookeeper_servers = 'localhost:2181',
                 cell = _cell_default):
        if cell is None:
            self._cell = self._cell_default
        else:
            self._cell = cell
        
        zookeeper.set_debug_level(zookeeper.LOG_LEVEL_ERROR)
        self._z = zookeeper.init(zookeeper_servers)

        self._recursivelyCreatePath('%s/machines/'%self._cell)
        self._recursivelyCreatePath('%s/jobs/'%self._cell)
        self._recursivelyCreatePath('%s/tasks/'%self._cell)

    def __del__(self):
        zookeeper.close(self._z)
        
    def create_machine(self, data, cell=_cell_default):
        if not isinstance(data, odin_pb2.Machine):
            raise TypeError('data must be a protobuffer Machine')
        machine = zookeeper.create(self._z,
                                   '%s/machines/m-'%cell,
                                   data.SerializeToString(),
                                   [ZOO_OPEN_ACL_UNSAFE],
                                   zookeeper.SEQUENCE | zookeeper.EPHEMERAL)

        machine_name = path_pop(machine)
        cell_name = path_cell(machine)

        zookeeper.create(self._z,
                         '%s/tasks/%s'%(cell_name, machine_name),
                         '',
                         [ZOO_OPEN_ACL_UNSAFE])
        return machine
        
    def register_machine(self, machine, data):
        if not isinstance(data, odin_pb2.Machine):
            raise TypeError('data must be a protobuffer Machine')
        zookeeper.create(self._z,
                         machine,
                         data.SerializeToString(),
                         [ZOO_OPEN_ACL_UNSAFE],
                         zookeeper.EPHEMERAL)

    def remove_machine(self, machine):
        try:
            zookeeper.delete(self._z,
                             machine)
            return True
        except zookeeper.NoNodeException:
            return False

    def get_machine(self, machine):
        return odin_pb2.Machine.FromString(zookeeper.get(self._z, machine)[0])

    def get_tasks(self, machine):
        machine_name = path_pop(machine)
        cell = path_cell(machine)
        tasks_dir = '%s/tasks/%s'%(cell, machine_name)

        children = zookeeper.get_children(self._z, tasks_dir)
        
        tasks = list()
        for child_id in children:
            child = '%s/%s'%(tasks_dir, child_id)
            tasks.append(self.get_task(child))
        
        return tasks

    def get_task(self, task):
        return odin_pb2.Task.FromString(zookeeper.get(self._z, task)[0])

    def watch_tasks(self, machine, watcher):
        machine_name = path_pop(machine)
        cell = path_cell(machine)
        tasks_dir = '%s/tasks/%s'%(cell, machine_name)

        children = zookeeper.get_children(self._z, tasks_dir, watcher)

        tasks = list()
        for child_id in children:
            tasks.append(child_id)
        
        return tasks

    def add_task_to_machine(self, task, machine):
        if not isinstance(task, odin_pb2.Task):
            raise TypeError('task must be a protobuffer Task')
        machine_name = path_pop(machine)
        cell_name = path_cell(machine)

        return zookeeper.create(self._z,
                                '%s/tasks/%s/t-'%(cell_name, machine_name),
                                task.SerializeToString(),
                                [ZOO_OPEN_ACL_UNSAFE],
                                zookeeper.SEQUENCE)

    def _recursivelyCreatePath(self, path, intermediate_data = ''):
        '''
        Should do a check to see if this dir already exists.
        '''
        current_path = ''
        for part in path.split('/'):
            if len(part) > 0:
                try:
                    current_path += '/' + part
                    zookeeper.create(self._z,
                                     current_path,
                                     intermediate_data,
                                     [ZOO_OPEN_ACL_UNSAFE])
                except zookeeper.NodeExistsException:
                   pass

class OdinMachine(threading.Thread):
    '''
    A machine that will run tasks given from the Odin cluster.
    '''

    _machine = None
    _odin = None
    _supervisor = None
    _supervisor_default_group = 'dynamic'
    _supervisor_methods = []
    _tasks = {}

    def __init__(self, machine = None, cell = None,
                 supervisor_url = "http://localhost:9001/RPC2"):
        threading.Thread.__init__(self)

        self._machine = machine
        self._supervisor = xmlrpclib.ServerProxy(supervisor_url) 
        self._supervisor_methods = self._supervisor.system.listMethods()

        self.reset_group()

        #rint self._supervisor_methods
        # Create an Odin connection.
        self._odin = Odin(cell = None)

        machine_data = odin_pb2.Machine()
        if self._machine is None:
            self._machine = self._odin.create_machine(machine_data)
        else:
            self._odin.register_machine(self._machine, machine_data)

    # PUBLIC Methods
    def has_twiddler(self):
        return 'twiddler.getAPIVersion' in self._supervisor_methods

    def create_process(self, name, config, group = _supervisor_default_group):
        return self._supervisor.twiddler.addProgramToGroup(group, name, config)
    
    def remove_process(self, name, group = _supervisor_default_group):
        return self._supervisor.supervisor.removeProcessFromGroup(group, name)
        
    def get_process_info(self, name, group = _supervisor_default_group):
        return self._supervisor.supervisor.getProcessInfo('%s:%s'%(group, name))
        
    def get_processes(self, group = _supervisor_default_group):
        return self._supervisor.supervisor.getAllProcessInfo()

    def get_log(self, name, group = _supervisor_default_group):
        return self._supervisor.supervisor.readProcessStderrLog(
            '%s:%s' % (group, name), 0, 0)

    def run(self):
        '''
        Thread runner.
        '''
        self.run_tasks(self._odin.watch_tasks(self._machine,
                                              self._tasks_watcher))

        while True:
            time.sleep(60)
            logger.debug('Heartbeat.')

    def reset_group(self, group = _supervisor_default_group):
        '''
        Stops all tasks and removes the group, adding it back.
        '''
        self._supervisor.supervisor.stopProcessGroup(group)

        processes = self.get_processes()
        for process in processes:
            if process['group'] == group:
                logger.debug('Stopping process %s' % process['name'])
                self._supervisor.twiddler.removeProcessFromGroup(
                    group, process['name'])

        self._supervisor.supervisor.removeProcessGroup(group)
        self._supervisor.supervisor.addProcessGroup(group)

    def task_to_config(self, task):
        config = dict()
        for key in ['command', 'directory', 'umask', 'priority', 'autorestart',
                    'startsecs', 'startretries', 'stopsignal', 'stopwaitsecs',
                    'user', 'redirect_stderr', 'stdout_logfile',
                    'stdout_logfile_maxbytes', 'stdout_logfile_backups',
                    'stdout_capture_maxbytes', 'stderr_logfile',
                    'stderr_logfile_maxbytes', 'stderr_logfile_backups',
                    'stderr_capture_maxbytes']:
            if task.runnable.HasField(key):
                config[key] = getattr(task.runnable, key)

        return config

    def get_task(self, task_id):
        machine_name = path_pop(self._machine)
        cell = path_cell(self._machine)
        task = '%s/tasks/%s/%s'%(cell, machine_name, task_id)

        return self._odin.get_task(task)

    def run_tasks(self, tasks):
        logger.debug('run_tasks on %s tasks.' % len(tasks))
        for task_id in tasks:
            if self._tasks.has_key(task_id):
                logger.debug('Already have task %s.' % task_id)
            else:
                logger.debug('New task %s. Let\'s start it.' % task_id)
                self._tasks[task_id] = self.get_task(task_id)

                config = self.task_to_config(self._tasks[task_id])
                print config
                self.create_process(task_id, config)

    # Private Methods
    def _tasks_watcher(self, z, event, state, path):
        '''
        Watcher for a change in tasks.
        '''
        
        #line =  (z, type(event), type(state), path)
        #logger.debug(line)
        logger.debug('Task List changed for %s.' % path)

        self.run_tasks(self._odin.watch_tasks(self._machine,
                                              self._tasks_watcher))


def signal_handler(self, signal, frame):
    print 'Kill signal received'
    sys.exit(0)

def main(argv = None):
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)

    logger.setLevel(logging.DEBUG)

    log_format = '%(asctime)s\t%(name)s:%(process)d\t%(filename)s:%(lineno)d\t%(levelname)s\t%(message)s'

    formatter = logging.Formatter(log_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info('Starting OdinMachine.')

    odin_machine = OdinMachine()
    odin_machine.start()
    task_1 = odin_pb2.Task()
    task_1.runnable.command = 'ls'
    task_1.runnable.startsecs = 0
    task_name = odin_machine._odin.add_task_to_machine(task_1,
                                                       odin_machine._machine)
    logger.debug('Added task %s'%task_name)
    odin_machine.join()
    logger.info('Threads joined.')

if __name__ == '__main__':
  main()
