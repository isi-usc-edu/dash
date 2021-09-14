import sys; sys.path.extend(['.;../../'])
import os
import collections
import socket
import json
from Dash2.core.des_work_processor import LocalWorkProcessor
#from evaluate import run_evaluation
from Dash2.posam.naive_agent import NaiveAgent
from Dash2.posam.process_agent import ProcessAgent

# Command line
import argparse

# handle paths nicely
from pathlib import Path

#DASH_ROOT=Path('/Users/abramson/research/venom/git/webdash/Dash2')
DASH_ROOT = Path('/Users/jim/Projects/Deter/webdash/Dash2')

def run_batch(experiment_runs, run_experiments, evaluation_on):
    global training_threshold
    # Run experiments (and optionally evaluation)
    for experiment_params in experiment_runs:
        if not os.path.exists(experiment_params["output_dir"]):
            os.mkdir(experiment_params["output_dir"])
        experiment_params['output_file_name'] = {}
        for repetition in range(experiment_params["repetitions"]):
            output_file_name = experiment_params["output_dir"] + 'simulation_' + experiment_params["model_name"]+".json"

            if experiment_params["repetitions"] > 1:
                output_file_name = output_file_name.replace(".json", str(repetition) + ".json")
                experiment_params['output_file_name'][repetition] = output_file_name

            if run_experiments:  # training_files, output_file_name, start_time, end_time, settings
                training_threshold = experiment_params["training_threshold"]  # Different for Enron and synthetic
                #agent = NaiveAgent(next_event_time_model=experiment_params["next_event_time_model"])
                agent = experiment_params["agent_class"](next_event_time_model=experiment_params["next_event_time_model"])
                work_processor = LocalWorkProcessor(output_file_name=output_file_name,
                                                    start_time=experiment_params['start_date'],
                                                    end_time=experiment_params['end_date'],
                                                    settings=experiment_params, agent=agent, verbose=True,
                                                    create_initial_state_fn=process_create_initial_state)
                work_processor.max_iterations = experiment_params['max_iterations']
                work_processor.run_experiment()

            if evaluation_on and experiment_params["ground_truth_file"] is not None:
                print("Evaluation ...")
                if not os.path.exists(experiment_params["output_dir"] + "evaluation/"):
                    os.mkdir(experiment_params["output_dir"] + "evaluation/")
                run_evaluation(experiment_params["output_dir"], output_file_name,
                               experiment_params["training_dir"] + experiment_params["training_file"],
                               experiment_params["ground_truth_file"])


# Should return a dictionary of agent data for each agent
def process_create_initial_state(training_data_path, initial_state_path):
    global training_threshold
    # Load events from training data and group by agent id
    training = [eval(line) for line in open(training_data_path)]
    agents = dict()
    for event in training[training_threshold:]:
        agent = event['filename'].split('maildir/')[-1].split('/')[0]
        pname = event['process:name']
        if agent in agents:
            ap = agents[agent]
            ap['events'] = ap['events'] + [event]
            if pname in ap['processes']:
                ap['processes'][pname] = ap['processes'][pname] + [event]
            else:
                ap['processes'][pname] = [event]
        else:
            agents[agent] = {'id': agent,
                             'events': [event], 'last_event_time': 0, 'processes': {pname: [event]}}
    # Once all the events are in, set the event rate and the counts for each action type, used by the naive agent
    for agent in agents:
        ap = agents[agent]
        ap['event_rate'] = len(training)/float(len(ap['events']))  # Need a normalizing factor based on number of seconds in the training period.
        ap['counts'] = collections.Counter([e['concept:name'] for e in ap['events']])
        # Set up book-keeping for the processes
        ap['current_process'] = []
        ap['process_count'] = 0
    return agents


def run_evaluation(experiment_dir_path, simulation_file_path, training_file_path, gt_file_path):
    pass



# Parse the command line options
def parse_args(args):
    parser = argparse.ArgumentParser(description="VENOM Demo for Jan 2021 Hackathon")
    parser.add_argument("--experiment_dir", "-e", 
                        type=str, 
                        # This default should only make sense on the final unix packaging
                        #default=str(DASH_ROOT / 'posam' ),
                        default='./',

                        help="Base experiment directory")

    # parser.add_argument("--logfile", "-l", 
    #                     type=str, 
    #                     default=str(DASH_ROOT / 'data' / 'concurlog.pickle'),
    #                     help="Path to pre-chewed process EventLog file")

    # parser.add_argument("--dataframe", "-d", 
    #                     type=str, 
    #                     default=str(DASH_ROOT / 'data' / 'concurlog.csv'),
    #                     required=False,
    #                     help="Pandas dataframe output file to write")

    
    # parser.add_argument("--run_experiments", "-r", 
    #                     help="If False, only evaluation will be done [OPTIONAL]",
    #                     required=False,
    #                     action='store_false')

    # parser.add_argument("--do_evaluation", "-d", 
    #                     help="If False, only similation will run [OPTIONAL]",
    #                     required=False,
    #                     action='store_true')

    # Thought we might want to subset by users, but perhaps not
    # parser.add_argument('-u','--users', 
    #                     nargs='+',
    #                     help='A list of users, separated by a space', 
    #                     required=False,
    #                     type=str,
    #                     default="gilbertsmith-d")


    return parser.parse_args(args)

def main(args):
    args = parse_args(args)
    print(args)

    # folder with training directory (with training files) and experiment directory (with simulation outputs) inside.
    base_experiment_dir = args.experiment_dir

    # Fetch these from the command line at some point
    run_experiments = True          # if False only evaluation will done
    evaluation_on = False           # if False only simulation will run
    bulk_postprocessing_on = True   # If True first run simulation then run evaluation (after all simulation runs are
                                    # complete). If True run evaluation after each simulation run.
    # Setup of each experiment run
    experiment_runs = [
        ################################################################################################
        ################################################################################################
        #####################             Test             #############################################
        ################################################################################################
        ################################################################################################
        ## model 1
        {"model_name":              "model_one",
         "agent_class":             NaiveAgent,
         "start_date":              "2020-05-01",  # simulation start date
         "end_date":                "2020-05-30",  # simulation end date, last day included
         "max_iterations":          111,
         "repetitions":             2,
         # simulation output dir path:
         "output_dir":              base_experiment_dir + 'experiment1/',
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir + "data/",
         "training_file":           "training.json",  # training/GT json (from GT script)
         "training_threshold":      270,
         "initial_state_file":      "initial_state.pickle", # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None,
         # agent behavior parameters:
         "next_event_time_model":   "flat_rate"},

        ################################################################################################
        ## model 2
        {"model_name":              "model_two",
         "agent_class":             ProcessAgent,
         "start_date":              "2020-05-01",  # simulation start date
         "end_date":                "2020-05-30",  # simulation end date, last day included
         "max_iterations":          111,
         "repetitions":             2,
         # simulation output dir path:
         "output_dir":              base_experiment_dir + 'experiment2/',
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir + "data/",
         "training_file":           "training.json",  # training/GT json (from GT script)
         "training_threshold":      270,
         "initial_state_file":      "initial_state.pickle", # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None,
         # agent behavior parameters:
         "next_event_time_model":   "flat_rate"},

        ################################################################################################
        ################################################################################################
        ###############  Run through the same models for the building domain    ########################
        ################################################################################################
        ################################################################################################
        ## model 1
        {"model_name":              "model_one",
         "agent_class":             NaiveAgent,
         "start_date":              "2020-05-01",  # simulation start date
         "end_date":                "2020-05-30",  # simulation end date, last day included
         "max_iterations":          250,
         "repetitions":             2,
         # simulation output dir path:
         "output_dir":              base_experiment_dir + 'building_experiment1/',
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir + "data/",
         "training_file":           "building_training.json",  # training/GT json (from GT script)
         "training_threshold":      0,
         "initial_state_file":      "initial_state.pickle",
         # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None,
         # agent behavior parameters:
         "next_event_time_model":   "flat_rate"},

        ################################################################################################
        ## model 2
        {"model_name":              "model_two",
         "agent_class":             ProcessAgent,
         "start_date":              "2020-05-01",  # simulation start date
         "end_date":                "2020-05-30",  # simulation end date, last day included
         "max_iterations":          250,
         "repetitions":             2,
         # simulation output dir path:
         "output_dir":              base_experiment_dir + 'building_experiment2/',
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir + "data/",
         "training_file":           "building_training.json",  # training/GT json (from GT script)
         "training_threshold":      0,
         "initial_state_file":      "initial_state.pickle",
         # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None,
         # agent behavior parameters:
         "next_event_time_model":   "flat_rate"},

        ################################################################################################

    ]
    
    run_batch(experiment_runs, run_experiments, evaluation_on)

if __name__ == "__main__":

    import sys
    main(sys.argv[1:])

    

    



