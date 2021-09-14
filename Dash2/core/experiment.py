import subprocess
import threading
import numbers
import math
import numpy
import time
import json
from Dash2.core.trial import Trial
from Dash2.core.parameter import Range
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.des_work_processor import WorkProcessor


# An experiment consists of a varying condition and for each condition a number of trials.
# trial.py shows how the trials can be customized, and phish_experiment.py gives an example of the experiment harness.


class Experiment(object):
    def __init__(self, trial_class=Trial, work_processor_class=WorkProcessor, exp_id=None, number_of_hosts=1,
                 independent=None, dependent=None, exp_data={}, num_trials=3,
                 file_output=None, hosts=None,
                 #experiment_file="/users/blythe/webdash/Dash2/pass_experiment.py",
                 dash_home="/users/blythe/webdash",
                 imports="",  # e.g. 'import pass_experiment',
                 callback=None,  # For multiple hosts, a default function calling each host is used if this is None
                 trial_class_str=None,  # If callback is not given, runs a generic experiment on this class for each host
                 reading_local_results=True,  # If False, results are being read as a string on another host
                 user="blythe", start_hub=None):
        self.goal = ""  # The goal is a declarative representation of the aim of the experiment.
                        # It is used where possible to automate experiment setup and some amount of validation.
        self.trial_class = trial_class
        self.exp_data = exp_data
        self.num_trials = num_trials
        self.trial_outputs = {}  # A dict with the independent variable as key
        # dependent may be a function of a trial or a member variable of the trial.
        self.independent = independent
        self.dependent = dependent
        self.hosts = hosts  # If there is a host list, assume it is for Magi on Deter for now
        self.dash_home = dash_home
        self.imports = imports
        self.callback = callback
        self.file_output = file_output
        self.trial_class_str = trial_class_str
        self.user = user
        #self.experiment_file = experiment_file
        self.start_hub = start_hub  # If not None, specifies a path to a hub that will be started if needed on each host
        # for distributed trials:
        self.exp_id = exp_id
        self.number_of_hosts = number_of_hosts
        self.completed_trials_counter = 0
        self.work_processor_class = work_processor_class




    # Run the experiment. If several hosts are named, parcel out the trials and independent variables
    # to each one and call them up. If none are named, we are running all of this here (perhaps
    # as part of a multi-host solution).
    def run(self, run_data={}, zk=None):
        if zk is not None: # run distributed trials
            self.run_distributed_trials(zk, run_data)
        else:
            if self.hosts is None or not self.hosts:
                return self.run_this_host(run_data)
            else:
                return self.scatter_gather(run_data) # run parallel trial (each trial is sequential)

    def run_distributed_trials(self, zk, run_data):
        if self.exp_id is None:
            next_id = zk.Counter("/nex_experiment_id_counter")
            self.exp_id = next_id.value
            next_id +=1

        zk.ensure_path("/experiments/" + str(self.exp_id) + "/status")
        zk.set("/experiments/" + str(self.exp_id) + "/status", "in progress")

        self.trial_outputs = {}
        # Build up trial data from experiment data and run data
        trial_data_for_all_values = self.exp_data.copy()
        for key in run_data:
            trial_data_for_all_values[key] = run_data[key]
        # Append different data for the independent variable in each iteration
        independent_vals = self.compute_independent_vals()
        for independent_val in independent_vals:
            trial_data = trial_data_for_all_values.copy()
            if self.independent is not None:
                trial_data[self.independent[0]] = independent_val
            self.trial_outputs[independent_val] = []
            for trial_number in range(self.num_trials):
                print("Trial ", trial_number, " with ", None if self.independent is None else self.independent[0], "=", independent_val)
                curr_trial_path = "/experiments/" + str(self.exp_id) + "/trials/" + str(trial_number)
                @zk.DataWatch(curr_trial_path + "/status")
                def watch_trial_status(data, stat_):
                    if data is not None and data != "":
                        data_dict = json.loads(data)
                        status = data_dict["status"]
                        if status == "completed":
                            print("Trial " + str(data_dict["trial_id"]) + " is complete")
                            trial_dependent = data_dict["dependent"]
                            print("Dependent evaluated to " + str(trial_dependent))
                            self.trial_outputs[independent_val].append(trial_dependent)
                            self.completed_trials_counter += 1
                            if (self.completed_trials_counter == self.num_trials):
                                print("All trials completed successfully")
                                print("Outputs: " + str(self.trial_outputs))
                                zk.set("/experiments/" + str(self.exp_id) + "/status", "completed")
                                zk.ensure_path("/experiments/" + str(self.exp_id) + "/dependent")
                                zk.set("/experiments/" + str(self.exp_id) + "/dependent", json.dumps(self.trial_outputs))
                                zk.delete("/experiments/" + str(self.exp_id) + "/trials", recursive = True)
                                self.completed_trials_counter = 0
                            return False
                    return True
                trial = self.trial_class(zk=zk, work_processor_class = self.work_processor_class, number_of_hosts=self.number_of_hosts, exp_id=self.exp_id, trial_id=trial_number, data=trial_data)
                trial.run()

        return self.exp_id

    # For now, create ssh calls in subprocesses for the other hosts.
    def scatter_gather(self, run_data={}):
        # For a second pass, split up the independent values among the hosts
        independent_vals = self.compute_independent_vals()
        all_threads = []
        i = 0  # index into independent_vals
        h = 0  # host index
        g = len(independent_vals) / len(self.hosts)
        rem = len(independent_vals) % len(self.hosts)
        # If there are more hosts than values, figure out how many hosts are being used per value
        # and divide up the number of trials. Each host here might do too much work but it's a start.
        trials = self.num_trials
        if g == 0:
            hosts_per_value = len(self.hosts) / len(independent_vals)
            trials = self.num_trials / hosts_per_value
        # Need to iterate over packets of work, probably single independent variable values and reduced trials
        # for now, so we can dole these out as machines finish tasks and faster machines naturally do more work.
        for host in self.hosts:
            # Gets a segment of the independent values (currently this leaves hosts unused if there are more
            # hosts than values, need to fix by combining with number of trials).
            num_vals = g + 1 if h < rem else max(g, 1)
            vals = [independent_vals[(j + i) % len(independent_vals)] for j in range(0, num_vals)]
            i += num_vals
            h += 1
            #time.sleep(1)  # so the printing routines don't overwrite each other
            print('will create a .aal file using host,', host, 'with vals', vals)
            #time.sleep(1)  # so the printing routines don't overwrite each other
            # But for now use ssh
            t = self.RunProcess(self, host, vals, trials)
            t.start()
            all_threads.append(t)
        # Wait for them all to finish
        for t in all_threads:
            t.join()
        # Collate the results
        all_data = [t.result for t in all_threads]
        print('++ all data is', all_data)
        # Data should be a dictionary indexed by independent variable of results for each host
        # (as returned by run_this_host). To gather, combine into one dictionary.
        combo = dict()
        for result in all_data:
            if result is not None:  # If a host failed, combine the remaining results
                for i in result:
                    if i in combo:
                        combo[i] += result[i]
                    else:
                        combo[i] = result[i]
        self.trial_outputs = combo
        return combo

    class RunProcess(threading.Thread):  # thread class for managing processes on another host

        def __init__(self, experiment, host, vals, num_trials):
            threading.Thread.__init__(self)
            self.experiment = experiment
            self.host = host
            self.vals = vals
            self.num_trials = num_trials  # May be less than experiment.num_trials if there are enough hosts
            self.print_all_lines = False
            self.result = None
            print('set up for', host, 'with vals', vals)

        # I'm having trouble sending the arguments, so this creates a custom file for each host,
        # relies on it having the same file system, and attempts to execute it on the host
        def run(self):
            filename = self.experiment.dash_home + "/Magi/Exp/f-" + self.host
            call = ["ssh", self.experiment.user+"@"+self.host, "python", filename]
            print('call is', call)
            with open(filename, 'w') as f:
                # for now, args is the set of independent variables this host will work on. Needs to be cleaned up.
                f.write('import sys\nsys.path.insert(0, \'' + self.experiment.dash_home +
                        '\')\nimport Dash2.core.experiment\nfrom Dash2.core.parameter import Range\n' + self.experiment.imports + '\n' +
                        # The callback has to be a function that takes these arguments
                        ('Dash2.core.experiment.run_local_part' if self.experiment.callback is None else self.experiment.callback) +
                        '(trial_class=' + str(self.experiment.trial_class_str) +
                        ', num_trials=' + str(self.num_trials) +
                        ', exp_data=' + str(self.experiment.exp_data) +
                        ', independent=[\'' + str(self.experiment.independent[0]) + '\', ' + str(self.vals) + ']' +
                        ', dependent=\'' + str(self.experiment.get_dependent_vars) + '\')\n')
            start = time.time()
            try:
                process = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            except BaseException as e:
                print('unable to run python subprocess:', e)
                return
            line = process.stdout.readline()
            self.result = None
            while line != "":
                if line.startswith("processed:"):
                    print('** getting data from', self.host, line)
                    self.result = eval(line[line.find('processed:') + 10:])
                elif line.startswith("print_through:"):
                    print('** print(through from', self.host, line)
                elif self.print_all_lines:
                    print(self.host, 'prints', line)
                line = process.stdout.readline()
            print(self.host, 'took', time.time() - start)
            print(process.communicate())

    # Runs a set of trials for each value of the independent variable, keeping all other values constant,
    # and returning the set of trial outputs.
    # run_data may be a function of the independent variable or a constant.
    def run_this_host(self, run_data={}):
        # Make sure there is a hub if needed
        hub_thread =  self.start_hub_if_needed()
        self.trial_outputs = {}
        # Build up trial data from experiment data and run data
        trial_data_for_all_values = self.exp_data.copy()
        for key in run_data:
            trial_data_for_all_values[key] = run_data[key]
        # Append different data for the independent variable in each iteration
        independent_vals = self.compute_independent_vals()
        # Dependent might be a method or a string representing a function or a member variable
        # If it's a string representing a function it's changed to the function. We don't pass this to another host.
        if isinstance(self.dependent, str):
            if hasattr(self.trial_class, self.dependent) and callable(getattr(self.trial_class, self.dependent)):
                print("Dependent is callable on the trial, so switching to the method")
                self.dependent = getattr(self.trial_class, self.dependent)
            elif not hasattr(self.trial_class, self.dependent):
                print("Dependent is not a callable method, but is a variable on the trial")
            else:
                print("Dependent is a string")
        else:
            print("dependent is not a string:", self.dependent)
        for independent_val in independent_vals:
            trial_data = trial_data_for_all_values.copy()
            if self.independent is not None:
                trial_data[self.independent[0]] = independent_val
            self.trial_outputs[independent_val] = []
            for trial_number in range(self.num_trials):
                print("Trial", trial_number, "with", None if self.independent is None else self.independent[0], "=", \
                    independent_val)
                trial = self.trial_class(data=trial_data)
                trial.run()
                trial_dependent = self.dependent(trial) if callable(self.dependent) else getattr(trial, self.dependent)
                if 'print_dependent' not in run_data or run_data['print_dependent']:
                    print("Dependent", self.dependent, "evaluated to", trial_dependent)
                self.trial_outputs[independent_val].append(trial_dependent)
        # Kill the hub process if one was created
        if hub_thread is not None:
            hub_thread.stop_hub()
        return self.trial_outputs

    def compute_independent_vals(self):
        independent_vals = [None]
        # The representation for independent variables isn't fixed yet. For now, a two-element list with
        # the name of the variable and a range object.
        if self.independent is not None and isinstance(self.independent[1], Range):
            #independent_vals = range(self.independent[1].min, self.independent[1].max, self.independent[1].step)
            # Need something that handles floats. Leaving the old code above in case this causes trouble
            independent_vals = numpy.arange(self.independent[1].min, self.independent[1].max, self.independent[1].step)
            print('expanded range to', independent_vals)
        elif self.independent is not None and isinstance(self.independent[1], (list, tuple)):  # allow a direct list
            independent_vals = self.independent[1]
        return independent_vals

    class HubThread(threading.Thread):  # thread class for managing a hub

        def __init__(self, process):
            threading.Thread.__init__(self)
            self.process = subprocess

        def run(self):
            line = self.process.stdout.readline()
            while line != "":
                print("hub:", line)
                line = self.process.stdout.readline()

        def stop_hub(self):
            self.process.stdin.write("q\n")
            self.process.communicate()

    def start_hub_if_needed(self):
        if self.start_hub is not None:
            # Create a DASH agent and attempt to register to see if there is a hub
            agent = DASHAgent()
            agent.register()
            if not agent.connected:
                print("** Starting hub on current host with", self.start_hub)
                try:
                    process = subprocess.Popen(["python", self.start_hub], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    line = process.stdout.readline()
                    while "if you wish" not in line:
                        print('hub:', line)
                        line = process.stdout.readline()
                    hub_thread = self.HubThread(process)
                    hub_thread.start()
                    return hub_thread
                except BaseException as e:
                    print('unable to run process for hub:', e)
        return None

    def process_results(self):  # After calling run(), use to process and return the results
        # If the results are a dictionary, assume the key is the independent variable and process the outcomes
        # for each one
        if self.trial_outputs and isinstance(self.trial_outputs, dict):
            result = dict()
            for key in self.trial_outputs:
                result[key] = process_list_results(self.trial_outputs[key])
            return result
        return process_list_results(self.trial_outputs)


def run_local_part(**args):
    print('local:', ['args from central were', args])
    exp = Experiment(args['trial_class'] if 'trial_class' in args else Trial,
                     exp_data=args['exp_data'] if 'exp_data' in args else None,
                     independent=args['independent'] if 'independent' in args else None,
                     dependent=args['dependent'] if 'dependent' in args else None,
                     num_trials=args['num_trials'] if 'num_trials' in args else 3,
                     reading_local_results=False)
    outputs = exp.run()
    print('processed:', outputs)


def process_list_results(list_results):
    # If each result is a list, zip them and attempt simple statistics on them
    if list_results and all([isinstance(x, (list, tuple)) for x in list_results]):
        print('iterating simple statistics on', list_results)
        return [simple_statistics([trial[i] for trial in list_results]) for i in range(len(list_results[0]))]
    elif list_results and all([isinstance(x, numbers.Number) for x in list_results]):
        return simple_statistics(list_results)
    else:
        return list_results


def simple_statistics(numlist):
    #print('running simple statistics on', numlist)
    if all([isinstance(x, numbers.Number) for x in numlist]):
        return [numpy.mean(numlist), numpy.median(numlist), numpy.var(numlist),
                numpy.std(numlist)/math.sqrt(len(numlist)),  # standard error
                len(numlist)]

