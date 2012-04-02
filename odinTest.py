#!/usr/bin/env python
# encoding: utf-8
"""
odinTest.py

Created by Stephen Holiday on 2012-03-27.
Copyright (c) 2012 Stephen Holiday. All rights reserved.

Attempts to follow the Google Python Style Guide:
http://google-styleguide.googlecode.com/svn/trunk/pyguide.html

Not because I think it's the best, but because it's a standard.
"""

import odin
import odin_pb2
import random
import unittest

class OdinTest(unittest.TestCase):
    def setUp(self):
        self.odin = odin.Odin(cell = '/odin/test%s'%random.randint(0,9999))
        self.machine_data = odin_pb2.Machine()
        self.machine_data_2 = odin_pb2.Machine()
        self.task_1 = odin_pb2.Task()
        self.task_1.id = 2

    def test_create_machine(self):
    	machine = self.odin.create_machine(self.machine_data)
    	self.assertEquals(self.machine_data, self.odin.get_machine(machine))

    def test_remove_machine(self):
    	machine = self.odin.create_machine(self.machine_data)
    	self.assertTrue(self.odin.remove_machine(machine))

    def test_register_machine(self):
    	machine = self.odin.create_machine(self.machine_data)
    	self.assertTrue(self.odin.remove_machine(machine))
    	self.odin.register_machine(machine, self.machine_data_2)
    	self.assertEquals(self.machine_data_2, self.odin.get_machine(machine))

    def test_add_task(self):
    	machine = self.odin.create_machine(self.machine_data)
    	task = self.odin.add_task_to_machine(self.task_1, machine)
    	task_name = odin.path_pop(task)
    	self.assertEquals(self.task_1, self.odin.get_tasks(machine)[0])

    def test_add_politician(self):
    	politician = self.odin.add_politician(odin_pb2.Politician())
    	politicians = self.odin.get_politicians()

    	self.assertIn(politician, politicians)

class OdinMachineTest(unittest.TestCase):
    def setUp(self):
        self.machine = odin.OdinMachine(cell =
        	'/odin/test%s'%random.randint(0,9999))
        self.task_1 = odin_pb2.Task()
        self.task_1.id = 2

    def test_has_twiddler(self):
    	self.assertTrue(self.machine.has_twiddler())

    def test_task_to_config(self):
    	task = odin_pb2.Task()
    	task.runnable.command = 'ls'
    	task.runnable.startsecs = 0

    	expected_conf = {'command' : 'ls', 'startsecs' : 0}
    	generted_conf = self.machine.task_to_config(task)

    	self.assertItemsEqual(generted_conf, expected_conf)

    def test_get_processes(self):
   		self.machine.get_processes()

    def test_get_task(self):
    	task = self.machine._odin.add_task_to_machine(self.task_1,
    												  self.machine._machine)
    	task_id = odin.path_pop(task)
    	self.assertEquals(self.task_1, self.machine.get_task(task_id))
  
if __name__ == '__main__':
    unittest.main()