import sys; sys.path.extend(['../../'])
import json
import collections
from Dash2.core.des_agent import DESAgent
import random
from Dash2.posam.utils import *


########################################################################################################################
# NaiveMixin agent
########################################################################################################################
class NaiveAgent(DESAgent):
    def __init__(self, **kwargs):
        DESAgent.__init__(self, **kwargs)
        self.next_event_time_model = kwargs.get("next_event_time_model", False)
        self.res_id_counter = 0
        self.new_user_id_counter = 1000000
        self.test_interval = None

    ####################################################################################################################
    # main agent's loop, overrides agent_decision_cycle(self, **kwargs) from DESAgent
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        """
        Called when agent is activated.
        :param agent_data:
        :param event_time:
        :param platform:
        :return:
        """
        agent_data = kwargs.get('agent_data', None)
        event_time = kwargs.get('event_time', None)

        if agent_data is not None and event_time is not None:
            #log_item = {'nodeUserID': agent_data['id'],
            #            'nodeID': None,
            #            'actionType': None,
            #            'nodeTime': str(event_time),
            #            'platform': platform}
            # Use the same format as the Venom Enron code for now, which is XES. Might need a more general format later.
            log_item = {'filename': agent_data['id'],
                        'concept:name': None,
                        'time:timestamp': str(event_time)}

            # pick action type based on frequency in counts
            #log_item['actionType'] = random.choice(['Submit', 'Approve', 'Pre-approve', 'Await (status:pending)', 'Review'])
            action_index = random.randrange(len(agent_data['events']))
            ttl = 0
            counts = agent_data['counts']
            for action in counts:
                ttl += counts[action]
                if ttl >= action_index:
                    break
            log_item['concept:name'] = action

            # pick nodeID (e.g. repo, tweet, email thread, etc.)
            log_item['nodeID'] = self._generate_node_id()

            self.log_event(log_item)
        else:
            raise AssertionError("decision_data_object and event_time and platform must not be None")

        self.event_counter += 1
        return False

    def log_event(self, log_data, log_file=None, format='json', verbose=False):
        json.dump(log_data, self.hub.json_log_file)
        self.hub.json_log_file.write("\n")

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

    def _generate_node_id(self):
        self.res_id_counter += 1
        return "r" + str(self.res_id_counter)
