import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent


# This agent demonstrates the use of mental models in reasoning about whether to take a security action. Mental models
# here use projection following Laird-Johnson. The 'project' rule below shows how the agent believes a
# self-taken action might change the world while 'trigger' rules show how exogenous actions triggered by world states
# may in turn change the world. The mental model(s) affect the rules through conditional clauses as shown
# in the trigger rule. Each model that the agent follows is declared as 'known' in the initial setup: uncomment one
# or both of the 'self.known' lines below to change the agent's mental models, which change its beliefs about the
# consequences of actions.


class SecurityUser(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)
        self.readAgent("""

goalWeight doWork 1

goalRequirements doWork
  decideEachStep([backUp(), engageFirewall(), followLink()])

goalRequirements decideEachStep([])

goalRequirements decideEachStep(plan)
  decideFirstStep(plan)
  remainder(plan, rest)
  decideEachStep(rest)

goalRequirements decideFirstStep(plan)
  preferFirstStep(plan, step)
  step

goalRequirements decideFirstStep(plan)
  succeed(_doNothing)

project followLink()
  + _got_data
  + _attacked

trigger _attacked
  _burglar_model and not performed(engageFirewall()) -> + _identity_stolen
  _vandal_model and not performed(backUp()) -> + _lost_files

utility
  _got_data -> 1
  _identity_stolen -> -1
  _lost_files -> -1

""")
        #self.known('_vandal_model')  # Assert the model(s) that the agent is using
        #self.known('_burglar_model')
        # Uncomment to see what's going on with the projection
        #self.traceProject = True

    # Binds the 'remainder' var to the remainder of the plan in the first var
    def remainder(self, args_tuple):
        (predicate, plan, remainder_var) = args_tuple
        if len(plan) < 1:
            return []
        else:
            return [{remainder_var: plan[1:]}]

    def back_up(self, goal):
        print('backing up')
        return [{}]

    def engage_firewall(self, goal):
        print('engaging firewall')
        return [{}]

    def follow_link(self, goal):
        print('followed link')
        return [{}]


if __name__ == "__main__":
    s = SecurityUser()
    s.agent_loop(max_iterations=10)
