import sys; sys.path.extend(['../../'])
import json
import collections
#from Dash2.core.des_agent import DESAgent
from Dash2.posam.utils import *
from Dash2.posam.naive_agent import NaiveAgent

# This agent currently just replays process traces, giving them new names based on the count, e.g. if the 5th process
# replayed by this agent was originally 'travel', this is called 'travel-5'. That may not be unique.


########################################################################################################################
# NaiveMixin agent
########################################################################################################################
class ProcessAgent(NaiveAgent):
    def __init__(self, **kwargs):
        NaiveAgent.__init__(self, **kwargs)
        # current_process is a list of actions remaining to be taken if we are in the middle of a process trace.
        # self.current_process = []
        # self.current_process_name = None
        # self.process_count = 0

    ####################################################################################################################
    # main agent's loop, overrides agent_decision_cycle(self, **kwargs) from NaiveAgent(DESAgent)
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

        if agent_data is not None and event_time is not None :
            #log_item = {'nodeUserID': agent_data['id'],
            #            'nodeID': None,
            #            'actionType': None,
            #            'nodeTime': str(event_time),
            #            'platform': platform}
            # Use the same format as the Venom Enron code for now, which is XES. Might need a more general format later.
            log_item = {'filename': agent_data['id'],
                        'concept:name': None,
                        'time:timestamp': str(event_time)}

            # pick action by following a process or picking a new one to follow.
            ap = agent_data
            if not ap['current_process']:
                process_to_follow = random.choice(list(ap['processes']))
                ap['current_process'] = ap['processes'][process_to_follow]
                ap['process_count'] += 1
                ap['current_process_name'] = process_to_follow + '-' + str(ap['process_count'])

            # Pick the next action from the current process
            log_item['concept:name'] = ap['current_process'][0]['concept:name']
            ap['current_process'] = ap['current_process'][1:]
            log_item['process:name'] = ap['current_process_name']

            # pick nodeID (e.g. repo, tweet, email thread, etc.)
            log_item['nodeID'] = self._generate_node_id()

            self.log_event(log_item)
        else:
            raise AssertionError("decision_data_object and event_time cannot be None")

        self.event_counter += 1
        return False
