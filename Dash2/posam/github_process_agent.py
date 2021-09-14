from Dash2.core.process import Process, ProcessInstance
from Dash2.core.process_agent import ProcessAgent
from pm4py.objects.petri.petrinet import PetriNet
from pm4py.objects.petri import utils
from Dash2.posam.utils import count_days, SECONDS_IN_DAY, random_pick
from Dash2.posam.github_probabilistic_agent import GithubProbabilisticAgent
import pickle
import random

########################################################################################################################
# Process class - describes process model as a Petrinet
########################################################################################################################
class GithubProcess(Process):
    name = "GithubProcess"

    def __init__(self, **kwargs):
        self.petri_net_file = kwargs.get('petri_net_file', None)
        if self.petri_net_file is not None:
            # create process by creating an Petri net
            with open(self.petri_net_file, 'rb') as f:
                net = pickle.load(f)

            # create action_roles
            action_roles = dict()
            all_roles = list(net.transitions)
            for t in net.transitions:
                if t.label is not None:
                    action_roles[str(t)] = [t]
                else:
                    action_roles[str(t)] = all_roles
            super().__init__(net, action_roles, GithubProcess.name)
        else:
            raise AssertionError("petri_net_file cannot be None")


########################################################################################################################
# Agent class
########################################################################################################################
class GithubProcessAgent(ProcessAgent):
    def __init__(self, **kwargs):
        self.next_event_time_model = kwargs.get("next_event_time_model", 'replay')
        self.new_issue_id_counter = 49123
        ProcessInstance.process_instance_id_counter = self.new_issue_id_counter
        self.test_interval = None
        default_processes_data = [{"class": GithubProcess, "max_instances": 1, "prob": 0.99}]
        supported_processes = kwargs.get("supported_processes", default_processes_data)
        kwargs['supported_processes'] = supported_processes
        super().__init__(**kwargs)

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
            agent_data['traces']['case:concept:name'].replace({issue_to_replace: self.new_issue_id_counter}, inplace=True)
            self.new_issue_id_counter += 1
            agent_data['issue_prob'].pop(issue_to_replace, None)


        if agent_data is not None and event_time is not None:
            log_data = {'time': event_time,
                        'transition': str(agent_data['traces'].loc[agent_data['t_index']]['concept:name']),
                        'agent_id': agent_data['id'],
                        'instance_id': int(agent_data['traces'].loc[agent_data['t_index']]['case:concept:name']),
                        }
            agent_data['t_index'] = (agent_data['t_index'] + 1) % len(agent_data['traces'])
            self.log_event(log_data)
        else:
            raise AssertionError("decision_data_object and event_time and platform must not be None")

        self.event_counter += 1
        return False # super().agent_decision_cycle(**kwargs) # default behavior

    ####################################################################################################################
    # Start new process instances
    ####################################################################################################################
    def start_new_process_instances(self, **kwargs):
        # domain specific instantiation of a process goes here
        return super().start_new_process_instances(**kwargs)

    ####################################################################################################################
    # Advance process instance by taking an action.
    ####################################################################################################################
    def advance_process(self, process_instance, time, src_place, agent_data, transitions_current_agent_can_fire=None,
                        verbose=True):
        # domain specific process transitions can be implemented here
        return super().advance_process(process_instance, time, src_place, agent_data, transitions_current_agent_can_fire,
                        verbose)

    ####################################################################################################################
    # Log event
    ####################################################################################################################
    def log_event(self, log_data, log_file=None, format='json', verbose=False):
        columns_renamed = dict()
        columns_renamed['time:timestamp'] = log_data['time']
        columns_renamed['concept:name'] = log_data['transition']
        columns_renamed['case:concept:name'] = log_data['instance_id']
        columns_renamed['org:resource'] = log_data['agent_id']
        columns_renamed['process:name'] = GithubProcess.name #log_data['process']
        super().log_event(columns_renamed, log_file=log_file, format=format, verbose=verbose)


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
        return GithubProbabilisticAgent.next_event_time(self, agent_data, curr_time, start_time, max_time)


# tests
if __name__ == "__main__":
    n_customers = 10
    n_representatives = 10

    # init agents
    processes_data = [{"class": GithubProcess, "max_instances": 1, "prob": 0.99}]
    employee_agent = GithubProcessAgent()
    employee_agent_data = [{"id": i, "roles": ["employee"]} for i in range(n_customers)]
    reviewer_agent = GithubProcessAgent(supported_processes=processes_data)
    reviewer_agent_data = [{"id": i + len(employee_agent_data), "roles": ["reviewer"]} for i in range(n_representatives)]

    # all agents and their data_objects
    agents = [(employee_agent, d) for d in employee_agent_data]
    agents.extend([(reviewer_agent, d) for d in reviewer_agent_data])

    employee_agent.agent_loop(max_iterations=21, agent_data=employee_agent_data[0], agents=agents, verbose=True)

