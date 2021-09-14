from Dash2.core.des_agent import DESAgent
from Dash2.posam.utils import *

import random
import pickle


########################################################################################################################
# Agent class
########################################################################################################################
class GithubProbabilisticAgent(DESAgent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.next_event_time_model = kwargs.get("next_event_time_model", 'flat_rate')
        self.new_issue_id_counter = 49123
        self.test_interval = None

    ####################################################################################################################
    # This is agent's individual decision step.
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        agent_data = kwargs.get('agent_data', None)
        event_time = kwargs.get('event_time', None)

        # update ongoing issues set
        if random.uniform(0.0, 1.0) < agent_data['prob_new_issue']:
            issue_to_replace = random.choice(list(agent_data['issue_prob'].keys()))
            agent_data['issue_prob'][self.new_issue_id_counter] = agent_data['issue_prob'][issue_to_replace]
            self.new_issue_id_counter += 1
            agent_data['issue_prob'].pop(issue_to_replace, None)

        if agent_data is not None and event_time is not None:
            log_data = {'time': event_time,
                        'transition': random_pick(agent_data['event_prob']),
                        'agent_id': agent_data['id'],
                        'issue_id': random_pick(agent_data['issue_prob'])
                        }
            self.log_event(log_data)
        else:
            raise AssertionError("decision_data_object and event_time and platform must not be None")

        self.event_counter += 1
        return False

    ####################################################################################################################
    # Log event
    ####################################################################################################################
    def log_event(self, log_data, log_file=None, format='json', verbose=False):
        columns_renamed = dict()
        columns_renamed['time:timestamp'] = log_data['time']
        columns_renamed['concept:name'] = log_data['transition']
        columns_renamed['case:concept:name'] = log_data['issue_id']
        columns_renamed['org:resource'] = log_data['agent_id']
        super().log_event(columns_renamed, log_file=log_file, format=format, verbose=verbose)

    ####################################################################################################################
    # overrides next_event_time(**kwargs) from DESAgent
    ####################################################################################################################
    def next_event_time(self, agent_data, curr_time, start_time, max_time):
        """
        Return time of the first event in the given interval. Result is either between start_time and max_time or None.
        None is returned when agent does not take actions in the given time interval.
        :param agent_data:
        :param curr_time:
        :param start_time:
        :param max_time:
        :return:
        """
        data_obj = agent_data
        # init time intervals
        if self.test_interval is None:
            number_of_days_in_simulation = count_days(start_time, max_time)
            self.test_interval = number_of_days_in_simulation * SECONDS_IN_DAY
        if 'burst_index' not in data_obj:
            data_obj['burst_index'] = 0

        #
        if self.next_event_time_model == "replay":
            if data_obj['time_intervals'] is None or data_obj['time_intervals'] == 0:
                return None

            next_event_time = curr_time + data_obj['time_intervals'][data_obj['burst_index']]
            data_obj['burst_index'] = (data_obj['burst_index'] + 1) % len(data_obj['time_intervals'])

            while next_event_time < start_time :
                next_event_time += data_obj['time_intervals'][data_obj['burst_index']]
                data_obj['burst_index'] = (data_obj['burst_index'] + 1) % len(data_obj['time_intervals'])
        elif self.next_event_time_model == "flat_rate":
            if data_obj['event_rate'] is None or data_obj['event_rate'] == 0:
                return None

            delta = float(SECONDS_IN_DAY) / float(data_obj['event_rate'])
            next_event_time = curr_time + delta

            while next_event_time < start_time:
                next_event_time += delta
        elif self.next_event_time_model == "fixed":
            next_event_time = curr_time
            while next_event_time + SECONDS_IN_DAY < start_time:
                next_event_time += SECONDS_IN_DAY

            next_event_time += SECONDS_IN_DAY
        else:
            raise ValueError("Unsupported value of next_event_time_model " + self.next_event_time_model)

        if max_time >= float(next_event_time) >= start_time:
            return int(next_event_time)
        else:
            return None

