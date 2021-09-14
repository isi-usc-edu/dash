import sys; sys.path.extend(['../../'])
import os.path
import os
import json
from Dash2.core.trial import Trial
from Dash2.socsim_core.output_event_log_utils import convert_pickle_to_json


# Socsim Trial decomposes trial into tasks and allocates them to DashWorkers
class SocsimTrial(Trial):
    parameters = []
    # all measures are considered depended vars, values are aggregated in self.results
    measures = []

    def initialize(self):
        # self.initial_state_file is defined via experiment_data
        if not os.path.isfile(self.initial_state_file):
            raise Exception("Initial state file was not found")
        initial_state_meta_data = json.load(open(self.initial_state_file))["meta"]
        print(initial_state_meta_data)
        self.users_ids = initial_state_meta_data["users_ids"]
        self.resource_ids = initial_state_meta_data["resource_ids"]
        # set up max ids
        self.set_max_repo_id(int(initial_state_meta_data["number_of_resources"]))
        self.set_max_user_id(int(initial_state_meta_data["number_of_users"]))
        self.is_loaded = True


    # this method defines parameters of individual tasks (as a json data object - 'data') that will be sent to dash workers
    def init_task_params(self, task_full_id, data):
        _, _, task_num = task_full_id.split("-")
        self.init_task_param("initial_state_file", self.initial_state_file, data)
        self.init_task_param("UR_graph_path", json.load(open(self.initial_state_file))["meta"]["UR_graph_path"], data)

    # partial_dependent is a dictionary of dependent vars
    def append_partial_results(self, partial_dependent):
        for measure in self.measures:
            if not (measure.name in self.results):
                self.results[measure.name] = 0
            self.results[measure.name] += float(partial_dependent[measure.name])

    def process_after_run(self):  # merge log files from all workers
        file_names = []
        number_of_files = self.number_of_hosts
        for task_index in range(0, number_of_files, 1):
            log_file_name = self.output_file_name + str(self.exp_id) + "-" + str(self.trial_id) + "-" + str(task_index + 1) + "_event_log_file.json"
            file_names.append(log_file_name)
        tmp_file_name = self.output_file_name + "tmp_output.pickle"

        if number_of_files == 1:
            print("renaming .. ", file_names[0], " -> ", tmp_file_name)
            os.rename(file_names[0], tmp_file_name)
            print("renamed ", file_names[0], " -> ", tmp_file_name)
        else:
            print("Multiprocess event lot not implemented.")

            exit(-1)

        output_file_name = self.output_file_name + "_trial_" + str(self.trial_id) + ".json"
        convert_pickle_to_json(events_file=tmp_file_name,
                               output_file_name=output_file_name,
                               team_name=self.team_name,
                               scenario=self.scenario,
                               domain=self.domain,
                               platform=self.platform)
        os.remove(tmp_file_name)

        # print(dependent vars (e.g. runtime and memory))
        dep_vars_file_name = self.output_file_name + "_trial_" + str(self.trial_id) + ".txt"
        dep_vars_file = open(dep_vars_file_name , 'w')
        for measure in self.measures:
            dep_vars_file.write(measure.name)
            dep_vars_file.write(":")
            dep_vars_file.write(str(self.results[measure.name]))
            dep_vars_file.write("\n")
        dep_vars_file.close()
        #all_exp_dep_vars.csv
        path_str = "" if self.output_file_name[0] != "/" else "/"
        dep_vars_file = open(path_str.join(a + "/" for a in str(self.output_file_name).split("/")[:-1]) + "all_exp_dep_vars.csv", 'a')
        dep_vars_file.write(str(self.exp_id))
        dep_vars_file.write(",")
        dep_vars_file.write(str(self.output_file_name).split("/")[-1])
        dep_vars_file.write(",")
        for measure in self.measures:
            dep_vars_file.write(str(self.results[measure.name]))
            dep_vars_file.write(",")
        dep_vars_file.write("-0\n")
        dep_vars_file.close()
