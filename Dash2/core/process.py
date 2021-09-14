import sys; sys.path.extend(['../../'])
import pickle
import json
import random
from pm4py.objects.petri.petrinet import PetriNet
from pm4py.objects.petri import utils, networkx_graph
from pm4py.objects.petri.exporter import exporter as pnml_exporter
from pm4py.visualization.petrinet import visualizer as pn_visualizer
from networkx.readwrite.json_graph import node_link_data


class Process(object):
    """
    This is process model class.
    """
    name = "Process"

    def __init__(self, petrinet_graph:PetriNet, action_roles:dict, name:str, **kwargs):
        """
        This is process model class, which consists of a petrinet_graph and action_roles.
        Two fields must be defined and populated in any Process object: self.graph, self.action_roles
        :param petrinet_graph: PetriNet object from pm4py.objects.petri.petrinet
        :param action_roles: dictionary that maps action name (or transition) to a list of roles
        """
        self.action_roles = action_roles
        self.petrinet = petrinet_graph
        self.name = name

    def get_petrinet(self):
        """
        :return: returns petrinet representation
        """
        return self.petrinet

    def print_graph(self, output_path="./process.svg"):
        """
        Prints csv file of petrinet graph.
        :param output_path:
        :return:
        """
        parameters = {pn_visualizer.Variants.WO_DECORATION.value.Parameters.FORMAT: "svg"}
        gviz = pn_visualizer.apply(self.petrinet, parameters=parameters)
        pn_visualizer.save(gviz, output_path)

    def get_roles(self):
        """
        :return: list of roles used in the process
        """
        roles = set()
        for rl in self.action_roles.values():
            roles.update(rl)
        return list(roles)

    def get_actions(self):
        """
        :return: list of actions (action names), list of strings
        """
        return list(self.action_roles.keys())

    def get_action_to_roles_dict(self):
        """
        :return: dictionary mapping action name to a list of roles
        """
        return self.action_roles

    def get_networkx_graph(self):
        """
        Return networkx graph and mapping of networkx nodes to places and transitions names
        :return: networkx graph, node_correspondance
        """
        G, node_correspondance = networkx_graph.create_networkx_directed_graph(self.petrinet)
        node_correspondance = {id: str(pl) for id, pl in node_correspondance.items()}
        return G, node_correspondance

    def to_dict(self):
        """
        Conver process model to dict object
        :return: dict
        """
        G, node_correspondance = self.get_networkx_graph()
        petrinet_dict ={"petrinet_networkx_graph": node_link_data(G), "networkx_node_names": node_correspondance,
                        "action_roles": self.action_roles}
        return petrinet_dict

    def to_json(self):
        """
        Convert process model to json object
        """
        json_str = json.dumps(self.to_dict())
        return json_str

    def to_str(self):
        """
        Convert process model to json string
        """
        return self.to_json()


class NaiveSendEmailProcess(Process):
    """
    This an example of a simple process of sending and receiving emails. It is a subclass of Process.
    Transition graph and action2roles mapping are defined in the __init__(). In reality these two parameters should be
    loaded from / saved to files and passed here as parameters.
    """
    name = "NaiveSendEmailProcess"

    def __init__(self):
        # create process by creating an Petri net
        net = PetriNet("new_petri_net")
        # creating source, after_send_place and sink place
        source = PetriNet.Place("source")
        sink = PetriNet.Place("sink")
        after_send_place = PetriNet.Place("after_send_place")
        # add the places to the Petri Net
        net.places.add(source)
        net.places.add(sink)
        net.places.add(after_send_place)
        # Create transitions
        send_transition = PetriNet.Transition("send_transition", "send_transition")
        reply_transition = PetriNet.Transition("reply_transition", "reply_transition")
        # Add the transitions to the Petri Net
        net.transitions.add(send_transition)
        net.transitions.add(reply_transition)
        # Add arcs
        utils.add_arc_from_to(source, send_transition, net)
        utils.add_arc_from_to(send_transition, after_send_place, net)
        utils.add_arc_from_to(after_send_place, reply_transition, net)
        utils.add_arc_from_to(reply_transition, sink, net)

        # create action_roles
        action_roles = {"send_transition": ["customer"], "reply_transition": ["representative"]}
        super().__init__(net, action_roles, NaiveSendEmailProcess.name)


class ProcessInstance(object):

    process_instance_id_counter = -1

    def __init__(self, process):
        self.process = process
        self.status = "not started"
        self.id = ProcessInstance.next_id()
        self.active_agents_marking = {str(p): set() for p in self.process.petrinet.places} # place is active if it has agents

        # history
        self.event_log = list() # history of all transitions/actions is kept here if keep_events_log_in_memory=False
        self.agent_process_roles = dict()

    @staticmethod
    def next_id():
        ProcessInstance.process_instance_id_counter += 1
        return ProcessInstance.process_instance_id_counter

    def advance(self, agents, time, agents_to_advance=None, keep_events_log_in_memory=False, verbose=False):
        """
        Advance the process. Transition all or a subset of active places. Steps:
        - Determine what transition (action) to fire.
        - Find an agent to execute an action if current agent cannot execute an action.
        - Execute action by calling proper agent method.
        - Update process status.

        :param agents: a dictionary of all available agents and their data objects. This set of agents will be used for
        role assignments.
        :param time:
        :param agents_to_advance: Subset of currently active agents, which advance the process.
        :param keep_events_log_in_memory:
        :param verbose:
        :return: None
        """
        if agents_to_advance is None:
            agents_to_advance = agents # consider all agents active.

        if self.status != "completed":
            for agent, agent_data in agents_to_advance:
                # find agent in current marking
                src_place = self.find_place_of_agent(agent_data)
                if src_place is not None:
                    # from current place find all outgoing transitions
                    transitions_current_agent_can_do = dict()
                    all_possible_transitions = dict()
                    for transition in src_place.out_arcs:
                        t_name = str(transition.target)
                        all_possible_transitions[t_name] = self.process.action_roles[t_name]
                        if set(self.process.action_roles[t_name]).issubset(agent_data['roles']):
                            transitions_current_agent_can_do[t_name] = self.process.action_roles[t_name]
                    # choose an agent
                    if len(transitions_current_agent_can_do) > 0: # if agent can execute some action, no need to choose a different agent
                        next_agent = agent
                        next_agent_decision_data = agent_data
                    else: # need to find an agent that can execute outgoing transitions from the current place.
                        # find agents that can continue each transitions
                        transitions_current_agent_can_do = None
                        all_possible_transitions_agents = dict()
                        for tr_name, roles in all_possible_transitions.items():
                            for a, a_data in agents:
                                if set(a_data['roles']).issubset(roles):
                                    if tr_name not in all_possible_transitions_agents:
                                        all_possible_transitions_agents[tr_name] = list()
                                    all_possible_transitions_agents[tr_name].append((a, a_data))
                        # uniform random pick of an agent
                        if len(all_possible_transitions_agents) > 0:
                            random_transition_name = random.choice(list(all_possible_transitions_agents.keys()))
                            next_agent, next_agent_decision_data = random.choice(all_possible_transitions_agents[random_transition_name])
                            # add this process instance to running instances list
                            if "running_processes" not in next_agent_decision_data:
                                next_agent_decision_data["running_processes"] = list()
                            next_agent_decision_data["running_processes"].append(self)
                            # update marking: replace current agent with next_agent
                            self.active_agents_marking[str(src_place)].remove(agent_data['id'])
                            self.active_agents_marking[str(src_place)].add(next_agent_decision_data['id'])
                        else:
                            print("Process cannot advance: cannot find an agent to make transition.")
                            return

                    # advance process by execute agent's action.
                    next_transition, dst_place = \
                        next_agent.advance_process(self, src_place=src_place, time=time, verbose=verbose,
                                                   agent_data=next_agent_decision_data,
                                                   transitions_current_agent_can_fire=transitions_current_agent_can_do)
                    # update marking:
                    self.active_agents_marking[str(src_place)].remove(next_agent_decision_data['id'])
                    self.active_agents_marking[str(dst_place)].add(next_agent_decision_data['id'])

                    # update agent to roles mapping
                    roles_played_in_transition = self.process.action_roles[str(next_transition)]
                    for r in roles_played_in_transition:
                        self.agent_process_roles[r] = next_agent

                    # Update actions_history and roles played by agents
                    if keep_events_log_in_memory:
                        event = {'transition': str(next_transition),
                                 'agent_id': agent_data['id'],
                                 'src': str(src_place),
                                 'dst': str(dst_place),
                                 'time': time,
                                 'instance_id': self.id,
                                 'process': str(self.process)}
                        self.event_log.append(event)

                else: # nothing to do, since agent is not currently involved in this process instance
                    pass

            # Update process status
            self.status = "completed"
            for k, v in self.active_agents_marking.items():
                if k != 'sink':
                    if len(v) > 0:
                        self.status = "in progress"
                        break
        else:
            print("Process is completed. Nothing to advance.")
        return

    def find_transition_by_name(self, transition_name):
        for t in self.process.petrinet.transitions:
            if str(t) == transition_name:
                return t
        return None

    def find_place_by_name(self, place_name):
        for p in self.process.petrinet.places:
            if str(p) == place_name:
                return p
        return None

    def find_place_of_agent(self, agent_data):
        for place, agents_in_place in self.active_agents_marking.items():
            if agent_data['id'] in agents_in_place:
                for p in self.process.petrinet.places:
                    if str(p) == place:
                        return p
        return None


# tests
if __name__ == "__main__":
    simple_process = NaiveSendEmailProcess()
    str_ = simple_process.to_str()
    json_str = simple_process.to_json()
    print(json_str)
    simple_process.print_graph("./tmp/process.svg")

