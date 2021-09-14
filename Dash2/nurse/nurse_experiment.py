import sys; sys.path.extend(['../../'])
import sys
from Dash2.core.experiment import Experiment
from Dash2.core.trial import Trial
from Dash2.core.client import Client
from Dash2.nurse.nurse01 import Nurse
from Dash2.core.parameter import Range


# To see the results, start a nurse_hub and run this file.


class NurseTrial(Trial):

    def __init__(self, data):
        Trial.__init__(self, data=data)
        self.iteration = 0  # crashes if not defined even if not used (to fix)
        self.max_iterations = -1
        self.experiment_client = Client()
        self.agents = []
        self.misses = []
        self.events = []
        self.computer_events = {}
        self.computer_misses = {}
        self.tick = 1

    def initialize(self):
        # Clear out/initialize the data on the hub
        self.experiment_client.register()
        self.experiment_client.sendAction("initWorld", (self.num_computers, self.num_medications, self.timeout))

        # Set up the agents. Each of n nurses is given a different list of k patients
        self.agents = [Nurse(ident=n,
                                     patients=["_p_" + str(n) + "_" + str(p) for p in range(1, self.num_patients + 1)])
                       for n in range(0, self.num_nurses)]
        for agent in self.agents:
            agent.active = True

    def process_after_agent_action(self, agent, action):
        if action is None:
            print('agent', agent, 'found no action, stopping')
            agent.active = False

    def agent_should_stop(self, agent):
        return not agent.active

    # After each step with every agent, cause the hub to go one 'tick', which is used to apply timeouts
    def process_after_iteration(self):
        self.experiment_client.sendAction("tick")
        #print "sent tick", self.tick
        self.tick += 1

    def process_after_run(self):
        global lt
        lt = self
        self.events = self.experiment_client.sendAction("showEvents")
        if self.events and self.events[0] == 'success':
            self.events = self.events[1]
        self.misses = len([e for e in self.events if e.patient != e.spreadsheet_loaded])
        print(self.misses, "misses out of", len([e for e in self.events if e.type in ["write", "read"]]), "reads and writes")
        # Find out which computers were used most heavily
        for event in self.events:
            if event.computer in self.computer_events:
                self.computer_events[event.computer].append(event)
            else:
                self.computer_events[event.computer] = [event]
            if event.patient != event.spreadsheet_loaded:
                if event.computer in self.computer_misses:
                    self.computer_misses[event.computer].append(event)
                else:
                    self.computer_misses[event.computer] = [event]
        print('computer, number of uses, number of misses')
        for ce in self.computer_events:
            print(ce, len(self.computer_events[ce]), len(self.computer_misses[ce]) if ce in self.computer_misses else 0)

    # This is the dependent function for testing the number of computers. It has to be a method so that it
    # can be evaluated in the final context where it is run - this file might not be imported but this class is available
    def test_num_computers_dependent(self):
        return (self.misses, self.tick)


# This spits out the results as the number of computers varies, creating a couple of hundred agents in the process.
# For the independent variable, the Range object gets expanded with python range()
def test_num_computers(hosts=None, num_trials=3, independent=['num_computers', Range(5, 21, 5)]):
    exp = Experiment(NurseTrial,
                     hosts=hosts,
                     exp_data={'num_nurses': 20, 'num_patients': 5, 'num_medications': 10, 'timeout': 0},  # was 20
                     independent=independent,
                     dependent='test_num_computers_dependent',
                     num_trials=num_trials,
                     # The imports must be sufficient to access the callback function (if any) and trial class.
                     imports='import nurse_experiment\nfrom nurse_hub import Event',
                     trial_class_str='nurse_experiment.NurseTrial')
    outputs = exp.run()
    #outputs = [[(t.timeout, t.num_computers, t.misses, t.iteration, len(t.events_of_type("login"))) for t in r]
    #          for r in runs]
    print("Experiment data:", exp.exp_data)
    print('print_through: outputs are', outputs)
    print("Number of computers, Number of misses, Number of iterations, Number of logins")
    for independent_val in sorted(outputs):
        print(independent_val, ":", outputs[independent_val])
    print('exp results:', exp.process_results())
    return exp, outputs


# This will be called back by the distribution code on each node.
# This is a completely generic function that I'm moving to experiment, passing the name of the trial class
#def test_num_computers_local(**args):
#    print 'local:', ['args from central were', args]
#    exp = Experiment(NurseTrial,
#                     exp_data=args['exp_data'] if 'exp_data' in args else None,
#                     independent=args['independent'] if 'independent' in args else None,
#                     dependent=args['dependent'] if 'dependent' in args else None,
#                     num_trials=args['num_trials'] if 'num_trials' in args else 3)
#    outputs = exp.run()
#    print 'processed:', outputs


def test_timeout():
    exp = Experiment(NurseTrial,
                     exp_data={'num_nurses': 20, 'num_patients': 5, 'num_medications': 10, 'num_computers': 20},
                     num_trials=8)
    #runs = [exp.run(run_data={'timeout': 65}) for t in range(0, 8)]  # looks like I wanted timeout to vary, coming back to that
    #outputs = [[(trial.timeout, trial.misses, trial.iteration,
    #             len(trial.events_of_type("login")), len(trial.events_of_type("autologout")))
    #            for trial in run]
    #           for run in runs]
    outputs = exp.run(run_data={'timeout': 65})
    print(outputs)


def run_one(hosts, num_trials=10, max_iterations=10, independent=None):
    return test_num_computers(hosts, num_trials=num_trials, independent=independent)

#timeout_runs = test_timeout()

#nc_runs = test_num_computers()

# can be called from the command line with e.g. the number of agents per trial.
if __name__ == "__main__":
    exp, results = run_one(sys.argv[1:], num_trials=3, max_iterations=10, independent=['num_computers', Range(4,20)])
    print('end process call')
