# A trial is a single trial in an experiment. Each trial has some setup that defines a list of agents,
# an iterative period where the agents are dovetailed until some stopping criterion is met,
# and an objective function that defines what gets saved from each trial and processed in the Experiment class.
import json
from Dash2.core.des_work_processor import WorkProcessor


class Trial(object):
    # Class-level information about parameter ranges and distributions.
    parameters = []
    measures = []

    def __init__(self, data={}, max_iterations=-1, zk=None, number_of_hosts=1, exp_id=None, trial_id=None,
                 work_processor_class=WorkProcessor, print_initial_data=True):
        self.agents = []
        self.data = data  # This passes parameter data to be used in the trial. The names are available as attributes
        # Initialize from parameter list first, then any passed data
        if hasattr(self.__class__, 'parameters') and self.__class__.parameters:
            print('initializing trial from parameters')
            for p in self.__class__.parameters:
                setattr(self, p.name, p.distribution.sample() if p.default is None else p.default)
        if print_initial_data:
            print('initializing trial with data', data)
        self.max_iterations = max_iterations
        for attr in data:
            setattr(self, attr, data[attr])
        self.iteration = 0
        self.zk = zk

        if zk is not None:
            self.exp_id = exp_id
            self.trial_id = trial_id
            self.curr_trial_path = "/experiments/" + str(self.exp_id) + "/trials/" + str(self.trial_id)
            self.zk.ensure_path(self.curr_trial_path)
            self.number_of_hosts = number_of_hosts
            self.received_tasks_counter = 0
            self.work_processor_class = work_processor_class

            self.zk.ensure_path(self.curr_trial_path + "/status")
            self.zk.set(self.curr_trial_path + "/status",
                        json.dumps({"trial_id": self.trial_id, "status": "in progress", "dependent": ""}))
            # set up max ids
            self.set_max_repo_id(0)
            self.set_max_user_id(0)

            # results dictionary will accumulate values of dependents variables.
            self.results = {}


    def set_max_repo_id(self, max_id):
        max_repo_id_path = "/experiments/" + str(self.exp_id) + "/" + str(self.trial_id) + "/" + str(
            self.trial_id) + "/max_repo_id"
        self.zk.ensure_path(max_repo_id_path)
        self.zk.set(max_repo_id_path, str(max_id))

    def set_max_user_id(self, max_id):
        max_user_id_path = "/experiments/" + str(self.exp_id) + "/" + str(self.trial_id) + "/" + str(
            self.trial_id) + "/max_user_id"
        self.zk.ensure_path(max_user_id_path)
        self.zk.set(max_user_id_path, str(max_id))

    # The initialize function sets up the agent list or initializes parameters for dash worker tasks (in zookeeper version)
    def initialize(self):
        pass

    # The trial's stopping criterion is met. By default, it checks each agent for a stopping
    # criterion and stops if either all the agents are ready to stop or a max iteration level is reached.
    def should_stop(self):
        if self.max_iterations > 0 and self.iteration >= self.max_iterations:
            print('reached end of iterations for trial')
            return True
        if self.agents:
            for a in self.agents:
                if not self.agent_should_stop(a):
                    return False
        if self.max_iterations > 0 and self.iteration < self.max_iterations:
            return False  # Follow the number of iterations by default
        else:
            return True

    # Default method for whether an agent should stop. By default, true, so if neither
    # this method nor should_stop are overridden, nothing will happen.
    def agent_should_stop(self, agent):
        return True

    # Default method to run one iteration of the trial: run one iteration of every active agent
    def run_one_iteration(self):
        for agent in self.agents:
            if not self.agent_should_stop(agent):
                next_action = agent.agent_loop(max_iterations=1, disconnect_at_end=False)  # don't disconnect since will run again
                self.process_after_agent_action(agent, next_action)

    def run(self):
        self.initialize()
        if self.zk is not None: # distributed trial version (uses zookeeper)
            self.run_distributed_trial()
            # self.process_after_run() - this method is called asynchronously via ZK watcher
        else: # overridden in each subclass to do something useful
            for agent in self.agents:
                agent.traceLoop = False
            while not self.should_stop():
                self.run_one_iteration()
                self.process_after_iteration()
                self.iteration += 1
            self.process_after_run()
            for agent in self.agents:
                agent.disconnect()

    def run_distributed_trial(self):
        # create a task for each node in experiment assemble
        task_number = 1  # task_number by default is the same as node id,
        # because by default each task in trial is assigned to exactly one node, but it might be different
        # in other implementations of Trial class
        for node_id in range(1, self.number_of_hosts + 1):
            task_full_id = str(self.exp_id) + "-" + str(self.trial_id) + "-" + str(task_number)
            task_path = "/tasks/nodes/" + str(node_id) + "/" + task_full_id
            dependent_vars_path = "/experiments/" + str(self.exp_id) + "/trials/" + str(
                self.trial_id) + "/nodes/" + str(node_id) + "/dependent_variables"
            self.zk.ensure_path(dependent_vars_path)

            task_data = {"work_processor_module": self.work_processor_class.module_name,
                         "work_processor_class": self.work_processor_class.__name__,
                         "max_iterations": self.max_iterations,
                         "task_full_id": task_full_id,
                         "parameters": []}
            for par in self.__class__.parameters:
                task_data[par.name] = getattr(self, par.name)  # parameter values are stored in task_data json object
                task_data["parameters"].append(par.name)  # work processor needs to know list of parameters (names)
            self.init_task_params(task_full_id, task_data)
            self.zk.ensure_path(task_path)
            self.zk.set(task_path, json.dumps(task_data))

            @self.zk.DataWatch(dependent_vars_path)
            def watch_dependent_vars(data, stat_):
                if data is not None and data != "":
                    self.received_tasks_counter += 1
                    # append partial results/dependent vars
                    task_results = json.loads(data)
                    node_id = task_results["node_id"]
                    partial_dependent = task_results["dependent"]
                    self.append_partial_results(partial_dependent)
                    dependent_vars_path = "/experiments/" + str(self.exp_id) + "/trials/" + str(
                        self.trial_id) + "/nodes/" + str(node_id) + "/dependent_variables"
                    self.zk.set(dependent_vars_path, "")  # clearing data
                    if self.received_tasks_counter == self.number_of_hosts: # all subtasks are completed.
                        self.aggregate_results()
                        self.zk.set(self.curr_trial_path + "/status", json.dumps(
                            {"trial_id": self.trial_id, "status": "completed", "dependent": self.results}))
                        self.process_after_run()
                        return False
                return True

            task_number += 1

    def init_task_params(self, task_full_id, data):
        pass

    def init_task_param(self, param_name, value, data):
        data[param_name] = value
        data["parameters"].append(param_name)

    # partial_dependent is a dictionary of dependent vars
    def append_partial_results(self, partial_dependent):
       pass

    def aggregate_results(self):
        pass

    def process_after_agent_action(self, agent, action):  # do any book-keeping needed after each step by an agent
        pass

    def process_after_iteration(self):  # do any book-keeping needed after each iteration completes
        pass

    def process_after_run(self):  # do any book-keeping needed after the trial ends and before agents are disconnected
        pass
