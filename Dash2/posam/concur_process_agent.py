from Dash2.core.process import Process
from Dash2.core.process_agent import ProcessAgent
from pm4py.objects.petri.petrinet import PetriNet
from pm4py.objects.petri import utils
import random

########################################################################################################################
# Process class - describes process as a Petrinet
########################################################################################################################
class ConcurProcess(Process):

    name = "ConcurProcess"

    def __init__(self):
        # create process by creating an Petri net
        net = PetriNet("new_petri_net")

        # creating source, p0-p4 and sink places
        source = PetriNet.Place("source")
        sink = PetriNet.Place("sink")
        p0 = PetriNet.Place("p0")
        p1 = PetriNet.Place("p1")
        p2 = PetriNet.Place("p2")
        p3 = PetriNet.Place("p3")
        p4 = PetriNet.Place("p4")
        net.places.add(source)
        net.places.add(sink)
        net.places.add(source)
        net.places.add(p0)
        net.places.add(p1)
        net.places.add(p2)
        net.places.add(p3)
        net.places.add(p4)

        # Create transitions
        submit = PetriNet.Transition("Submit", "Submit")
        review = PetriNet.Transition("Review", "Review")
        preapprove = PetriNet.Transition("Pre-approve", "Pre-approve")
        await_ = PetriNet.Transition("Await (status:pending)", "Await (status:pending)")
        approve = PetriNet.Transition("Approve", "Approve")

        # Add the transitions to the Petri Net
        net.transitions.add(submit)
        net.transitions.add(review)
        net.transitions.add(preapprove)
        net.transitions.add(await_)
        net.transitions.add(approve)

        # Add arcs
        utils.add_arc_from_to(source, submit, net)  # t0
        utils.add_arc_from_to(submit, p0, net)  # t1
        utils.add_arc_from_to(p0, review, net)  # t2
        utils.add_arc_from_to(review, p1, net)  # t3
        utils.add_arc_from_to(p1, preapprove, net)  # t4
        utils.add_arc_from_to(preapprove, p2, net)  # t5
        utils.add_arc_from_to(p2, await_, net)  # t6
        utils.add_arc_from_to(await_, p3, net)  # t7
        utils.add_arc_from_to(p3, approve, net)  # t8
        utils.add_arc_from_to(approve, sink, net)  # t9
        utils.add_arc_from_to(await_, p4, net)  # t10
        utils.add_arc_from_to(p4, review, net)  # t11
        utils.add_arc_from_to(submit, p3, net)  # t12
        utils.add_arc_from_to(review, p3, net)  # t13
        utils.add_arc_from_to(preapprove, p3, net)  # t14

        # create action_roles
        action_roles = {"Submit": ["employee"],
                        "Review": ["reviewer"],
                        "Pre-approve": ["reviewer"],
                        "Await (status:pending)": ["reviewer"],
                        "Approve": ["reviewer"]}
        super().__init__(net, action_roles, ConcurProcess.name)


########################################################################################################################
# Agent class
########################################################################################################################
class ConcurProcessAgent(ProcessAgent):
    def __init__(self, **kwargs):
        default_processes_data = [{"class": ConcurProcess, "max_instances": 1, "prob": 0.99}]
        supported_processes = kwargs.get("supported_processes", default_processes_data)
        kwargs['supported_processes'] = supported_processes
        super().__init__(**kwargs)

    ####################################################################################################################
    # This is agent's individual decision step.
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        return super().agent_decision_cycle(**kwargs) # default behavior

    ####################################################################################################################
    # Start new process instances
    ####################################################################################################################
    def start_new_process_instances(self, agent_data):
        # domain specific instantiation of a process goes here
        return super().start_new_process_instances(agent_data)

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
        columns_renamed['case:nodeID'] = log_data['agent_id']
        columns_renamed['process:name'] = log_data['process']
        super().log_event(columns_renamed, log_file=log_file, format=format, verbose=verbose)


# tests
if __name__ == "__main__":
    n_customers = 10
    n_representatives = 10

    # init agents
    processes_data = [{"class": ConcurProcess, "max_instances":1, "prob": 0.99}]
    employee_agent = ConcurProcessAgent()
    employee_agent_data = [{"id": i, "roles": ["employee"]} for i in range(n_customers)]
    reviewer_agent = ConcurProcessAgent(supported_processes=processes_data)
    reviewer_agent_data = [{"id": i + len(employee_agent_data), "roles": ["reviewer"]} for i in range(n_representatives)]

    # all agents and their data_objects
    agents = [(employee_agent, d) for d in employee_agent_data]
    agents.extend([(reviewer_agent, d) for d in reviewer_agent_data])

    employee_agent.agent_loop(max_iterations=21, agent_data=employee_agent_data[0], agents=agents, verbose=True)

