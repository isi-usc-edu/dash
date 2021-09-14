import sys; sys.path.extend(['../../'])
import time
import json
import gc
from kazoo.client import KazooClient
import logging
logging.basicConfig()

class DashWorker(object):

    # class level insformation
    module_name = "Dash2.core.dash_worker"

    def __init__(self, zk_hosts='127.0.0.1:2181', host_id=1):
        self.zk = KazooClient(zk_hosts)
        self.zk.start()
        self.zk_hosts = zk_hosts
        self.host_id = host_id
        self.status = "active"

    def run(self):
        # allowed values for "/experiment_assemble_status" are "active" and "terminated"
        self.zk.ensure_path("/experiment_assemble_status")
        self.status, stat = self.zk.get("/experiment_assemble_status")

        if self.status is None or self.status == '':
            self.zk.set("/experiment_assemble_status", "active")
            self.status = "active"

        if self.status == "terminated":
            self.zk.stop()
            return
        elif self.status == "active":
            node_prefix = "/tasks/nodes/" + str(self.host_id)
            self.zk.ensure_path(node_prefix)

            @self.zk.ChildrenWatch(node_prefix)
            def watch_tasks(tasks):
                if tasks is not None:
                    # TBD need to check and skip tasks that are already in progress
                    for task_id in tasks:
                        @self.zk.DataWatch(node_prefix + "/" + task_id)
                        def watch_task_update(data, stat_):
                            if data is not None and data != "":
                                self.process_tasks(data)
                                return False
                            return True
                return True

            @self.zk.DataWatch("/experiment_assemble_status")
            def watch_assemble_status(data, stat_):
                print("New status is %s" % data)
                if data == "terminated":
                    print("Node was terminated by experiment assemble status change")
                    self.status = data
                    return False
                return True

            while self.status == "active":
                print("Waiting for tasks ... \nTo terminate dash nodes change /experiment_assemble_status to 'terminated' via ExperimentController\n")
                time.sleep(60)
            self.zk.stop()
            return
        else:
            raise ValueError('/experiment_assemble_status contains incorrect value')

    def process_tasks(self, data):
        args = json.loads(data)
        module_name = args["work_processor_module"]
        class_name = args["work_processor_class"]
        task_full_id  = args["task_full_id"]
        processor_class = self.retrieve_work_processor_class(module_name, class_name)

        print("Received task " + task_full_id + " with data " + data)
        processor = processor_class(zk=self.zk, host_id=self.host_id, task_full_id=task_full_id, data=args)
        node_prefix = "/tasks/nodes/" + str(self.host_id)
        self.zk.ensure_path(node_prefix + "/" + task_full_id + "/status")
        self.zk.set(node_prefix + "/" + task_full_id + "/status", json.dumps({"status":"in progress", "iteration":0, "update time":0}))

        processor.process_task()

        self.zk.delete(node_prefix + "/" + task_full_id + "/status", recursive=True)
        self.zk.delete(node_prefix + "/" + task_full_id, recursive=True)

        gc.collect()
        print("Task " + str(task_full_id) + " is complete.")

    @staticmethod
    def retrieve_work_processor_class( module_name, class_name):
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        return cls


if __name__ == "__main__":
    print("running experiment ...")
    if len(sys.argv) == 1: # no parameters. 127.0.0.1:2181 is a default zookeeper server, 1 - default node id
        node = DashWorker()
        node.run()
    elif len(sys.argv) == 2:  # If one argument is given, it defines current host id. 127.0.0.1:2181 is a default zookeeper server here.
        curr_host_id = int(sys.argv[1])

        node = DashWorker(host_id=curr_host_id)
        node.run()
    elif len(sys.argv) == 3: # If two arguments were given, 2nd argument is a comma separated list of hosts, 1st argument is the current host's id (number between 1-1024)
        curr_host_id = int(sys.argv[1])
        hosts_list = sys.argv[2]

        node = DashWorker(zk_hosts=hosts_list, host_id=curr_host_id)
        node.run()
    else:
        print('incorrect arguments: ', sys.argv)

