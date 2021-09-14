import sys
sys.path.extend(['../../']) # need to have 'webdash' directory in $PYTHONPATH, if we want to run script (as "__main__")

import random
from Dash2.core.system2 import System2Agent
from Dash2.core.system1 import System1Agent
from Dash2.core.human_traits import HumanTraits
from Dash2.core.sem_agent import SEMAgent
from Dash2.core.dash_action import DASHAction
from Dash2.core.des_agent import DESAgent
from semopy.examples import political_democracy
desc = political_democracy.get_model()
data = political_democracy.get_data()



########################################################################################################################
# Use case #1: Using custom implementations of System 1 or System 2
#
# Step 1: create a custom subclass of System 1 and/or System 2 (doesn't have to be a subclass, but must have same interface)
# Step 2: create a MixinDASHAction class (descendant from DASHAction and new System 1(2) impl) that overrides __init__()
# Step 3: create a custom MyDASHAgent class, add or inherit any customized agent's behavior (attributes and methods here)
########################################################################################################################

class MyS1(System1Agent):
    # init my new system 1 class
    def __init__(self):
        System1Agent.__init__(self)
        # init my custom attributes here ...

    # implement custom behavior here ...
    # For example implement/override my own decay function (e.g. do decay twice):
    def system1_decay(self):
        for _ in range(2):
            for node in self.nodes:
                node.apply_decay()


class MyMixinDASHAction(DASHAction, MyS1):
    def __init__(self):
        # optionally do prior init here...
        DASHAction.__init__(self, system1_class=MyS1) # MyS1.__init()__ will be called inside DASHAction.__init__
        # optionally do post init ...

        # alternatively it is possible to implement custom action __init__ if special behavior or init order is needed:
        # Client.__init__(self)
        # # do something ...
        # System2Agent.__init__(self)
        # # do something ...
        # MyS1.__init__(self) # replaced original S1 with MyS1
        # # do something ...


class MyDASHAgent(MyMixinDASHAction, HumanTraits):
    def __init__(self):
        HumanTraits.__init__(self)
        MyMixinDASHAction.__init__(self)

    # optionally override any interface method (e.g. agent_loop(), agent_decision_cycle(), next_event_time() )
    # and implement primitive actions here ...


########################################################################################################################
# Use case #2: new agent with Discrete Event Simulation (DES) agent with custom agent_decision_cycle() method.
########################################################################################################################
class MyDESAgent(DESAgent):

    def __init__(self, **kwargs):
        DESAgent.__init__(self, **kwargs)

    def agent_decision_cycle(self, **kwargs):
        agent_data = kwargs.get('agent_data', None)
        event_time = kwargs.get('event_time', None)
        if agent_data is None or event_time is None:
            raise AssertionError("decision_data_object and event_time cannot be None")

        action = random.choice(['Submit', 'Approve', 'Pre-approve', 'Await (status:pending)', 'Review'])
        log_item = {'actionType': action, 'nodeTime': str(event_time)}
        print(log_item)
        self.event_counter += 1
        return action



########################################################################################################################
# Use case #3: Simple Structural Equation Model agent.
########################################################################################################################
class SimpleSEMAgent(SEMAgent):
    """
    NaiveSEMAgent - example from https://semopy.com/predict.html
    """

    def __init__(self, **kwargs):
        SEMAgent.__init__(self)
        self.readSemModel(""" 
# measurement model
ind60 =~ x1 + x2 + x3
dem60 =~ y1 + y2 + y3 + y4
dem65 =~ y5 + y6 + y7 + y8
# regressions
dem60 ~ ind60
dem65 ~ ind60 + dem60
# residual correlations
y1 ~~ y5
y2 ~~ y4 + y6
y3 ~~ y7
y4 ~~ y8
y6 ~~ y8
                        """) # prediction model
        self.readSemModel(desc) # just to test
        training_data = data # initial training data
        self.trainModel(training_data)

    def prediction_to_actions(self, preds):
        #TODO: convert [dem60, dem65, ind60] predictions into action(s)
        return [] # should return list of callable actions



if __name__ == "__main__":
    # Use case #1: Using custom implementations of System 1 or System 2
    uc1_agent = MyDASHAgent()
    uc1_agent.agent_loop(max_iterations=10)

    # Use case #3:
    uc2_agent = MyDESAgent()
    uc2_agent.agent_loop(max_iterations=10, agent_data={})

    # # Use case #3:
    # uc3_agent = SimpleSEMAgent()
    # uc3_agent.agent_loop()
