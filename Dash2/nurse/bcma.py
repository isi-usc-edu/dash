import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isVar


class BCMAAgent(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)
        self.readAgent("""

goalWeight doWork 1

goalRequirements doWork
  deliverMeds(_joe, _percocet)
  deliverMeds(_brian, _codeine)

goalRequirements deliverMeds(patient, medication)
  notKnown(document(patient, medication))
  buildPlan(patient, medication, plan)
  doFirstStepIfPreferred(plan)
  decidePerformRest(plan)

# These are probably general subgoals that should be available to all agents
goalRequirements doFirstStepIfPreferred(plan)
  preferFirstStep(plan, step)  # returns false or binds the step to perform
  step

# The second clause for the same goal is tried after the first one
# fails.
goalRequirements doFirstStepIfPreferred(plan)
  succeeds(_doNothing)

# Breaks the recursion
goalRequirements decidePerformRest([])

goalRequirements decidePerformRest(plan)
  remainder(plan, rest)
  doFirstStepIfPreferred(rest)
  decidePerformRest(rest)

# For envisioning a plan, relative to a mental model
# If there's no rule for an action under certain conditions, 
#  the 'performed' predicate is added for the action but nothing else
# To delete a fact, put a minus sign '-' in front of the fact.
# The model is a precondition like any other fact, but is not added or deleted.

project deliver(meds, patient)
  performed(retrieveMeds(meds, patient)) -> + performed(deliver(meds, patient))

# This turns off the default of adding 'performed(..)'
project deliver(meds, patient)

project ensureLoggedIn
  + _loggedIn

project document(meds, patient)
  performed(eMAR_Review(patient)) and performed(scan(patient))
  and performed(scan(meds)) and _loggedIn -> + performed(document(meds, patient))

project document(meds, patient)
  _nurseModel and performed(scan(patient)) and performed(scan(meds))
  and _loggedIn -> + performed(document(meds, patient))

project document(meds, patient)
  _nurseModel and _loggedIn -> 0.95 + performed(document(meds, patient))

project document(meds, patient)

# Still experimenting with this. This version is additive, e.g. each match to the given pattern
# in the final world increases the utility by the shown amount (decreases if negative)
utility
  performed(document(meds, patient)) -> 1

""")
        self.primitiveActions([[x, self.succeed] for x in ['eMAR_Review', 'retrieveMeds', 'scan', 'deliver',
                                                           #'ensureLoggedIn',
                                                           'document', 'succeeds', 'doNothing']])
        #self.traceProject = True


    # assume patient is bound and plan is not. Return bindings
    # for the plan
    def build_plan(self, args_tuple):
        (predicate, patient, meds, plan) = args_tuple
        print("calling build plan with", patient, meds)
        # instantiates the plan for the patient and meds
        if isVar(plan):
            return [{plan: [('eMAR_Review', patient),
                            ('retrieveMeds', meds, patient),
                            ('scan', patient),
                            ('scan', meds),
                            ('deliver', meds, patient),
                            ('ensureLoggedIn',),  # The comma is needed to force this action to be a tuple
                            ('document', meds, patient)]}]
        else:
            return []

    # Binds the 'remainder' var to the remainder of the plan in the first var
    def remainder(self, args_tuple1):
        (predicate, plan, remainder_var) = args_tuple1
        if len(plan) < 1:
            return []
        else:
            return [{remainder_var: plan[1:]}]

    def ensure_logged_in(self, goal):
        # Just assert that the agent is logged in right now
        self.known('_loggedIn')
        return [{}]


if __name__ == "__main__":
    a = BCMAAgent()
    a.agent_loop(max_iterations=200)
