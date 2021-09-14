import random
from Dash2.core.des_agent import DESAgent
from Dash2.core.process import Process, ProcessInstance, NaiveSendEmailProcess


class ProcessAgent(DESAgent):
    """
    Process-driven agent. This API defines the following methods:
    - agent_decision_cycle(self, **kwargs)
    - advance_process()
    """
    id_counter = -1

    def __init__(self, **kwargs):
        DESAgent.__init__(self, **kwargs)
        self.supported_processes = kwargs.get("supported_processes", [])

    ####################################################################################################################
    # This is agent's individual decision step.
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        """
        Called when agent is activated.
        """
        # Inputs:
        event_time = kwargs.get('event_time', None)
        agent_data = kwargs.get('agent_data', None) # pd dataframe
        verbose = kwargs.get('verbose', False)
        # agents is a list of tuples: [(agent_class: agent_decision_data) ... ]
        agents = kwargs.get('agents', list()) # all other agents visible to this agent

        # call advance_process for each active process
        if "running_processes" not in agent_data:
            agent_data["running_processes"] = list()
        for process_instance in agent_data["running_processes"]:
            if process_instance.status != "completed":
                process_instance.advance(agents=agents, time=event_time, agents_to_advance=[(self, agent_data)],
                                         keep_events_log_in_memory=False, verbose=verbose)

        # activate new process instances
        self.start_new_process_instances(**kwargs)

        self.event_counter += 1

        return False

    ####################################################################################################################
    # Start new process instances
    ####################################################################################################################
    def start_new_process_instances(self, **kwargs):
        agent_data = kwargs.get('agent_data', None)
        def _number_of_running_instances(p_name, instances):
            counter = 0
            for p in instances:
                if p.process.name == p_name and p.status != "completed":
                    counter += 1
            return counter

        for process_data in self.supported_processes:
            if _number_of_running_instances(process_data['class'].name, agent_data["running_processes"]) < process_data['max_instances'] and \
                    random.uniform(0, 1) < process_data['prob']:
                cls = process_data['class']
                process = cls(**kwargs)
                process_instance = ProcessInstance(process)
                process_instance.active_agents_marking['source'].add(agent_data['id'])
                agent_data["running_processes"].append(process_instance)

    ####################################################################################################################
    # Advance process instance by taking an action.
    ####################################################################################################################
    def advance_process(self, process_instance, time, src_place, agent_data, transitions_current_agent_can_fire=None,
                        verbose=True):
        """
        Determine what transition to fire given a process instance and agent’s state. Default implementation uses simple
        probabilistic transition choice. Assumption: if agent is assigned an action it can do it, no role check is done.
        This method is called by ProcessInstance.advance() method.
        :param process_instance:
        :param time: time of the event
        :param src_place: current place in the petrinet of the process
        :param agent_data:
        :param transitions_current_agent_can_fire: a subset of transitions agent can fire
        :param verbose:
        :return: next_transition, dst_place in the process petrinet
        """
        # input check
        if transitions_current_agent_can_fire is None:
            transitions_current_agent_can_do = dict()
            for transition in src_place.out_arcs:
                t_name = str(transition.target)
                if set(process_instance.process.action_roles[t_name]).issubset(agent_data['roles']):
                    transitions_current_agent_can_do[t_name] = process_instance.process.action_roles[t_name]
            transitions_current_agent_can_fire = transitions_current_agent_can_do

        # choose transition/action
        next_transition_name = random.choice(list(transitions_current_agent_can_fire.keys()))
        next_transition = process_instance.find_transition_by_name(next_transition_name)

        #choose target/dst place
        all_accessible_dst_places = [dst_p.target for dst_p in next_transition.out_arcs]
        dst_place = random.choice(all_accessible_dst_places)

        # execute action (call agent's action method if such exists)
        self.perform_action(next_transition_name)

        # log event
        event = {'transition': str(next_transition),
                 'agent_id': agent_data['id'],
                 'src': str(src_place),
                 'dst': str(dst_place),
                 'time': time,
                 'instance_id': process_instance.id,
                 'process': process_instance.process.name}
        self.log_event(event, format='json', verbose=verbose)

        return next_transition, dst_place


# tests
if __name__ == "__main__":
    n_customers = 10
    n_representatives = 10

    supported_processes = [{"class": NaiveSendEmailProcess, "max_instances":1, "prob": 0.99}]
    customer_agent = ProcessAgent(log_file="./tmp/log.json", supported_processes=supported_processes)
    customer_agent_data = [{"id": i, "roles": ["customer"]} for i in range(n_customers)]
    representative_agent = ProcessAgent(log_file="./tmp/log.json", supported_processes=supported_processes)
    representative_agent_data = [{"id":i + len(customer_agent_data), "roles": ["representative"]} for i in range(n_representatives)]

    # all agents and their data_objects
    agents = [(customer_agent, d) for d in customer_agent_data]
    agents.extend([(representative_agent, d) for d in representative_agent_data])

    customer_agent.agent_loop(max_iterations=21, agent_data=customer_agent_data[0], agents=agents, verbose=True)


