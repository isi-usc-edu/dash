import sys
sys.path.extend(['../../']) # need to have 'webdash' directory in $PYTHONPATH, if we want to run script (as "__main__")
import json
import time
import os
from datetime import  datetime
from heapq import heappush, heappop
from pathlib import Path

MAX_NUMBER_OF_ITERATIONS = 15000000


# WorkProcessor class is responsible for running experiment trial on a node in cluster (distributed/parallel trial)
class WorkProcessor:
    def __init__(self, zk, host_id, task_full_id, data):
        self.agents = []
        self.zk = zk
        self.host_id = host_id
        self.exp_id, self.trial_id, self.task_num = task_full_id.split("-") # self.task_num by default is the same as node id
        self.task_full_id = task_full_id
        self.max_iterations = int(data["max_iterations"])
        for param in data["parameters"] :
            if is_number(data[param]):
                setattr(self, param, float(data[param]))
            else:
                setattr(self, param, str(data[param]))

        #self.log_file = open(task_full_id + '_event_log_file.txt', 'w')
        self.iteration = 0
        # init agents and their relationships with repos

    def initialize(self):
        # subclasses must initialize their own communication hub
        # self.hub = ZkRepoHub(zk, task_full_id, 0, log_file=self.log_file)
        pass

    def process_task(self):
        self.initialize()
        if self.zk is not None and self.task_full_id is not None:
            while not self.should_stop():
                self.run_one_iteration()
                self.process_after_iteration()
                self.iteration += 1
                if self.iteration % 100000 == 0 :
                    node_path = "/tasks/nodes/" + str(self.host_id) + "/" + self.task_full_id
                    self.zk.ensure_path(node_path + "/status")
                    self.zk.set(node_path + "/status", json.dumps({"status": "in progress", "iteration": self.iteration, "update time": time.time()}))
                    print("Iteration " + str(self.iteration) + " " \
                          + str({"status": "in progress", "iteration": self.iteration, "update time": time.strftime("%H:%M:%S", time.gmtime(time.time()))}))

            self.process_after_run()

            result_path = "/experiments/" + str(self.exp_id) + "/trials/" + str(self.trial_id) + "/nodes/" + str(self.host_id) + "/dependent_variables/"
            dep_vars = self.get_dependent_vars()
            task_result = {"node_id":self.host_id, "dependent":dep_vars}
            data = json.dumps(task_result)
            self.zk.set(result_path, data)
        else:
            raise Exception("Zookeeper is not initialized.")

    def should_stop(self):
        if self.max_iterations > 0 and self.iteration >= self.max_iterations:
            print('reached end of iterations for trial')
            return True
        if self.max_iterations > 0 and self.iteration < self.max_iterations:
            return False  # Follow the number of iterations by default
        else:
            return True

    def run_one_iteration(self):
        # dummy implementation, override in subclass
        for agent in self.agents:
            if not self.agent_should_stop(agent):
                next_action = agent.agent_decision_cycle(max_iterations=1, disconnect_at_end=False)  # don't disconnect since will run again
                self.process_after_agent_action(agent, next_action)

    def get_dependent_vars(self):
        pass # override this method to populate values of dependent variables
        return {}

    # Default method for whether an agent should stop. By default, true, so if neither
    # this method nor should_stop are overridden, nothing will happen.
    def agent_should_stop(self, agent):
        return True

    def process_after_agent_action(self, agent, action):  # do any book-keeping needed after each step by an agent
        pass

    def process_after_iteration(self):  # do any book-keeping needed after each iteration completes
        pass

    def process_after_run(self):  # do any book-keeping needed after the trial ends and before agents are disconnected
        pass # self.log_file.close()


# Discrete event simulation work processor.Work processor performs simulation as individual process
class LocalWorkProcessor(object):

    def __init__(self, output_file_name, start_time, end_time, agent, create_initial_state_fn, settings=None, **kwargs):
        self.agents_data = {} # decision data objects; each agent's state is kept in agent's data object
        self.events_heap = [] # work queue for discrete event simulation
        self.event_counter = 0 # counter of events logged into output file
        self.iteration = 0 # how many times agent loop was called
        self.max_iterations = kwargs.get('max_iterations', MAX_NUMBER_OF_ITERATIONS) # max number of times agent's loop can be called.
        verbose = kwargs.get('verbose', True)
        self.time = start_time # global event clock
        self.env = dict() # environment object
        self.agent = agent
        self.agent.hub = self
        # simulation start and end time:
        self.start_time = time.mktime(datetime.strptime(str(start_time) + ' 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())
        self.max_time = time.mktime(datetime.strptime(str(end_time) + ' 23:59:59', "%Y-%m-%d %H:%M:%S").timetuple())
        # output file:
        self.output_file_name = output_file_name
        self.json_log_file = open(self.output_file_name, 'w')

        # create initial state, load it from dataframe
        self.agents_data = create_initial_state_fn(kwargs["training_file"], kwargs["initial_state_file"], **kwargs)
        self.agents_data_tuples = [(self.agent, d) for d in self.agents_data.values()]

        # populate queue (initial state)
        for agent_id in self.agents_data.keys():
            if 'last_event_time' in self.agents_data[agent_id]:
                let = self.agents_data[agent_id]['last_event_time']
                last_event_time = int(let)#time.mktime(datetime.strptime(str(let), "%Y-%m-%d %H:%M:%S").timetuple())
                next_event_time = self.agent.next_event_time(agent_data=self.agents_data[agent_id],
                                                             curr_time=last_event_time,
                                                             start_time=self.start_time,
                                                             max_time= self.max_time)
                if next_event_time is not None:
                    heappush(self.events_heap, (next_event_time, agent_id))

        if verbose:
            print("INFO: Agents instantiated ", str(len(self.agents_data)))

    def run_experiment(self):
        while not self.should_stop():
            self.run_one_iteration()
            self.iteration += 1
            if self.iteration % 1000 == 0:
                print("Iteration ", str(self.iteration), " ",
                      str({"iteration": self.iteration,
                           "update time": time.strftime("%H:%M:%S", time.gmtime(time.time())),
                           "experiment time": str(datetime.fromtimestamp(self.time).strftime("%Y-%m-%d %H:%M:%S")) }))
        self.process_after_run()

    def run_one_iteration(self):
        if self.agent is None:
            raise ValueError('WorkProcessor.agent is None.')

        event_time, agent_id = heappop(self.events_heap)
        self.set_curr_time(event_time)
        self.agent.agent_decision_cycle(agent_data=self.agents_data[agent_id], event_time=event_time, agents=self.agents_data_tuples)
        next_event_time = self.agent.next_event_time(agent_data=self.agents_data[agent_id],
                                                     curr_time=event_time,
                                                     start_time=self.start_time,
                                                     max_time=self.max_time)
        if next_event_time is not None:
            heappush(self.events_heap, (next_event_time, agent_id))
        self.event_counter += 1

    def should_stop(self):
        if self.max_iterations > 0 and self.iteration >= self.max_iterations:
            print('reached end of iterations for trial')
            return True
        if len(self.events_heap) == 0:
            print('reached end of event queue, no more events')
            return True
        return False

    def set_curr_time(self, curr_time):
        self.time = curr_time

    def process_after_run(self):  # do any post processing before closing the output file
        self.json_log_file.close() # close log


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
