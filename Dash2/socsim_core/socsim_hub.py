import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub
#from Dash2.github_baseline.zk_repo import ZkRepo
from Dash2.socsim_core.output_event_log_utils import random_pick_sorted
import datetime
import _pickle as pickle


# Zookeeper hub for socsim agents
class SocsimHub(WorldHub):
    """
    A class that handles client requests and modifies the desired repositories
    """

    sync_event_counter = 0

    def __init__(self, zk, task_full_id, start_time, output_file_name):
        WorldHub.__init__(self, None)
        self.trace_handler = False
        #ZkRepo.sync_event_callback = self.event_counter_callback
        self.zk = zk
        self.task_full_id = task_full_id
        self.exp_id, self.trial_id, self.task_num = task_full_id.split("-")  # self.task_num by default is the same as node id

        self.csv_log_file = open(output_file_name + self.task_full_id + '_event_log_file.csv', 'w')
        self.json_log_file = open(output_file_name + self.task_full_id + '_event_log_file.json', 'w')

        # global event clock
        self.time = start_time

        # for single process only
        self.graph = None
        self.topPopularResources = None
        self.userIdAndPopularity = None
        self.aggregated_statistic = {}
        self.users_ids = None # int id to str id map. Depending on implementation it can be populated by work processor.
        self.resource_ids = None # int id to str id map. Depending on implementation it can be populated by work processor.

    def finalize_statistics(self):
        if self.userIdAndPopularity is not None:
            random_pick_sorted(self.userIdAndPopularity["ids"], self.userIdAndPopularity["probability"])
        for var_data in self.aggregated_statistic.itervalues():
            aggregation_function = var_data["func"]
            if aggregation_function is not None:
                aggregation_function(var_data, self.aggregated_statistic, isFinalUpdate=True)

    def set_curr_time(self, curr_time):
        self.time = curr_time

    def event_counter_callback(self):
        pass

    def close_event_log(self):
        self.csv_log_file.close()
        self.json_log_file.close()

    def log_event(self, user_id, resource_id, event_type, time, additional_attributes=None):
        self.print_to_csv_log(user_id, resource_id, event_type, self._convert_time(time), additional_attributes)
        self.print_to_json_log(user_id, resource_id, event_type, int(time), additional_attributes)

    def print_to_csv_log(self, user_id, resource_id, event_type, time, additional_attributes):
        self.csv_log_file.write(time)
        self.csv_log_file.write(",")
        self.csv_log_file.write(event_type)
        self.csv_log_file.write(",")
        self.csv_log_file.write(str(user_id))
        self.csv_log_file.write(",")
        self.csv_log_file.write(str(resource_id))
        self.csv_log_file.write("\n")

    def print_to_json_log(self, user_id, resource_id, event_type, time, additional_attributes):
        json_object = {"nodeID": str(self._try_to_convert_resource_id_to_original_id(resource_id)),
                       "nodeUserID": str(self._try_to_convert_user_id_to_original_id(user_id)),
                       "actionType": str(event_type),
                       "nodeTime": str(time)}
        if additional_attributes is not None:
            json_object.update(additional_attributes)
        pickle.dump(json_object, self.json_log_file)

    def _convert_time(self, time):
        date = datetime.datetime.fromtimestamp(time)
        str_time = date.strftime("%Y-%m-%d %H:%M:%S")
        return str_time

    def _try_to_convert_user_id_to_original_id(self, user_id):
        if self.users_ids is not None:
            return self._convert_from_int_id(user_id, self.users_ids)
        else:
            return str(user_id)

    def _try_to_convert_resource_id_to_original_id(self, resource_id):
        if self.resource_ids is not None:
            return self._convert_from_int_id(resource_id, self.resource_ids)
        else:
            return str(resource_id)

    def _convert_from_int_id(self, entity_id, dictionary):
        if entity_id is not None and entity_id in dictionary:
            str_id = dictionary[entity_id]
        else:
            str_id = entity_id
        return str_id

    def processRegisterRequest(self, agent_id, aux_data):
        creation_time = self.time
        return ["success", aux_data["id"], creation_time]
