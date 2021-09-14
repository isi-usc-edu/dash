import sys; sys.path.extend(['../../'])
import os
import time
import json
from kazoo.client import KazooClient
import logging
logging.basicConfig()

# DashController is a until class that provides command line interface to run the experiment on clusters
# It allows to stop the experiment, check status of the experiment, check status of the nodes (dash workers)
class DashController:
    # zk_hosts - Comma-separated list of hosts of zookeeper to connect to
    # hosts - Comma-separated list of hosts available in experiment
    # Default value for host id is 1 which is a leader's id
    def __init__(self, zk_hosts='127.0.0.1:2181', number_of_hosts=1):
        # zookeeper connection is a process level shared object, all threads use it
        self.zk = KazooClient(zk_hosts)
        self.zk.start()

        self.zk_hosts = zk_hosts
        self.number_of_zk_hosts = len(zk_hosts.split(","))

        self.number_of_hosts = number_of_hosts
        self.result_evaluator = None #ResultEvaluator()
        self.continue_right_away = False

    def run(self, experiment, run_data={}, start_right_away=True, continue_right_away=False):
        self.continue_right_away = continue_right_away
        if start_right_away:
            print("ExperimentController: setting up the experiment ...")
            self.start_experiment(experiment, run_data)
        while True:
            cmd = input("Press \n\tq to exit experiment controller, \n\tt to terminate all worker nodes,"
                        "\n\ta to allow nodes run in background (change worker nodes assemble status to active),\n\ts to see experiment status, "
                        "\n\tc to remove all data from zookeeper (clean up storage for new experiments)"
                        "\n\tr to run experiment again."
                        "\n\te to run evaluation.\n")
            if cmd == "q":
                print("Exiting experiment controller")
                self.zk.stop()
                return
            elif cmd == "t":
                self.zk.set("/experiment_assemble_status", "terminated")
            elif cmd == "a":
                self.zk.set("/experiment_assemble_status", "active")
            elif cmd == "s":
               self.show_status()
            elif cmd == "e":
               self.run_evaluation()
            elif cmd == "c":
                self.clean_storage()
            elif cmd == "r":
                if experiment is not None:
                    print("Running experiment again ...")
                    self.start_experiment(experiment, run_data)
                else:
                    print("Experiment object not defined.")
            else:
                print("Unrecognized command " + cmd + "\n")



    def set_experiment_completion_watcher(self, exp_id):
        @self.zk.DataWatch("/experiments/" + str(exp_id) + "/status")
        def watch_status_change(data, _):
            if data == "completed":
                self.end_time = time.time()
                self.time = self.end_time - self.start_time
                self.zk.ensure_path("/experiments/" + str(exp_id) + "/time")
                self.zk.set("/experiments/" + str(exp_id) + "/time", json.dumps({"start": self.start_time, "end": self.end_time, "time": self.time}))
                print("Experiment " + str(exp_id) + " is complete. Time " + str(self.time) + " s.")
                if self.continue_right_away:
                    print("Experiment is complete and current process is being terminated ...")
                    os.system("kill " + str(os.getpid()))
                return False
            else:
                print("Experiment " + str(exp_id) + " status: " + str(data))
                return True

    def start_experiment(self, experiment, run_data):
        self.zk.ensure_path("/experiments")
        experiment.exp_id = len(self.zk.get_children("/experiments"))

        self.zk.ensure_path("/experiments/" + str(experiment.exp_id) + "/status")
        self.zk.set("/experiments/" + str(experiment.exp_id) + "/status", "queued")

        self.set_experiment_completion_watcher(experiment.exp_id)
        self.start_time = time.time()

        experiment.run(zk=self.zk, run_data=run_data)
        print("ExperimentController: experiment in progress")

    def clean_storage(self):
        print("Cleaning up zookeeper storage ...")
        if self.zk.exists("/experiments"):
            self.zk.delete("/experiments", recursive=True)
        self.zk.ensure_path("/experiments")
        if self.zk.exists("/tasks/nodes"):
            nodes = self.zk.get_children("/tasks/nodes")
            for node_id in nodes:
                if self.zk.exists("/tasks/nodes/" + str(node_id)):
                    tasks = self.zk.get_children("/tasks/nodes/" + str(node_id))
                    for task in tasks:
                        self.zk.delete("/tasks/nodes/" + str(node_id) + "/" + str(task), recursive=True)
        self.zk.ensure_path("/tasks/nodes")
        self.zk.ensure_path("/experiment_assemble_status")
        self.zk.set("/experiment_assemble_status", "active")

        next_id = self.zk.Counter("/nex_experiment_id_counter")
        next_id -= next_id.value
        print("Previous experiments removed")

    def run_evaluation(self):
        print("Running evaluation ...")
        self.result_evaluator.run()


    def show_status(self):
        if self.zk.exists("/experiments"):
            all_exps = self.zk.get_children("/experiments")
            if len(all_exps) == 0:
                print("no experiments found")
            else:
                # experiments status
                for exp in all_exps:
                    if self.zk.exists("/experiments/" + str(exp) + "/status"):
                        status, stat = self.zk.get("/experiments/" + str(exp) + "/status")
                        self.zk.ensure_path("/experiments/" + str(exp) + "/time")
                        raw_time, _ = self.zk.get("/experiments/" + str(exp) + "/time")
                        if self.zk.exists("/experiments/" + str(exp) + "/dependent") is None:
                            dependent = ""
                        else:
                            dependent, _ = self.zk.get("/experiments/" + str(exp) + "/dependent")
                        print("Experiment " + str(exp) + " status: " + str(status) + ". Time " + str(raw_time) + " (sec). \n  Dependent: " + str(dependent))

        else:
            print("no experiments found")
        # nodes status
        if self.zk.exists("/tasks/nodes"):
            nodes = self.zk.get_children("/tasks/nodes")
            for node_id in nodes:
                tasks = self.zk.get_children("/tasks/nodes/" + str(node_id))
                for task in tasks:
                    try:
                        task_status = "/tasks/nodes/" + str(node_id) + "/" + str(task) + "/status"
                        if self.zk.exists(task_status):
                            raw_status, _ = self.zk.get(task_status)
                            st = json.loads(raw_status)
                            print("Node " + str(node_id) + " tasks: " + str(tasks) + " - iteration: " + str(st["iteration"]) \
                                  + ", last update: " + str(time.strftime("%b %d %Y %H:%M:%S", time.gmtime(float(st["update time"])))))
                        else:
                            print("No status for " + str(task_status) + ". Task has not been accepted by worker.")
                    except Exception as err:
                        print("Error " + str(err))
