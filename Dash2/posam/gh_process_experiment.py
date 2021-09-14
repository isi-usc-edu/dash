import sys; sys.path.extend(['.;../../'])
import os
import collections
import socket
import pickle
from pathlib import Path
import json
from Dash2.core.des_work_processor import LocalWorkProcessor
#from evaluate import run_evaluation
from Dash2.posam.github_process_agent import GithubProcessAgent, GithubProcess
from Dash2.posam.github_probabilistic_agent import GithubProbabilisticAgent
from Dash2.posam.create_initial_state import create_initial_state
from Dash2.posam.utils import convert_json_into_df


# Command line
import argparse

# handle paths nicely
from pathlib import Path

# DASH root path, currently not used
DASH_ROOT=Path('./Dash2')
# path to data folder with inputs and outputs for the simulation
DASH_POSAM_ROOT=Path('.')


def run_batch(experiment_runs, run_experiments, evaluation_on):
    global training_threshold
    # Run experiments (and optionally evaluation)
    for experiment_params in experiment_runs:
        if not os.path.exists(Path(experiment_params["output_dir"])):
            os.mkdir(Path(experiment_params["output_dir"]))
        experiment_params['output_file_names'] = {}
        for repetition in range(experiment_params["repetitions"]):
            output_file_name = Path(experiment_params["output_dir"], 'simulation_'+experiment_params["model_name"]+".json")

            if experiment_params["repetitions"] > 1:
                output_file_name = Path(str(output_file_name).replace(".json", str(repetition) + ".json"))
                experiment_params['output_file_names'][repetition] = output_file_name

            if run_experiments:
                # setup process model
                agent = experiment_params["agent_class"](
                    supported_processes=[{"class": GithubProcess, "max_instances": 1, "prob": 0.99}],
                    petri_net_file=experiment_params["process_model"] if "process_model" in experiment_params else None)
                # start work processor
                work_processor = LocalWorkProcessor(output_file_name=output_file_name,
                                                    start_time=experiment_params['start_date'],
                                                    end_time=experiment_params['end_date'],
                                                    settings=experiment_params,
                                                    agent=agent,
                                                    create_initial_state_fn=create_initial_state,
                                                    verbose=True, **experiment_params)
                work_processor.run_experiment()
                convert_json_into_df(output_file_name) # convert json to pandas dataframe and pickle it to file.

            if evaluation_on and experiment_params["ground_truth_file"] is not None:
                print("Evaluation ...")
                if not os.path.exists(Path(experiment_params["output_dir"], "evaluation")):
                    os.mkdir(Path(experiment_params["output_dir"], "evaluation"))
                run_evaluation(experiment_params["output_dir"], output_file_name, experiment_params["training_file"],
                               experiment_params["ground_truth_file"])


def run_evaluation(experiment_dir_path, simulation_file_path, training_file_path, gt_file_path):
    pass


# Parse the command line options
def parse_args(args):
    parser = argparse.ArgumentParser(description="VENOM Demo for July 2021 Hackathon")
    parser.add_argument("--experiment_dir", "-e",
                        type=str,
                        # This default should only make sense on the final unix packaging
                        default=str(DASH_POSAM_ROOT / 'experiment_github' ),
                        #default='./',
                        help="Base experiment directory")

    parser.add_argument("--training", "-t",
                        type=str,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'training_traces.zip',
                        help="Training traces file name. Format: pickled pandas dataframe.")

    parser.add_argument("--initial_state", "-s",
                        type=str,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'initial_state.zip',
                        help="Initial state file (python pickled object).")

    parser.add_argument("--process_model", "-m",
                        type=str,
                        default=str(DASH_POSAM_ROOT / 'experiment_github' / 'model.pickle'),
                        help="Path to petri net process model (in pickle format).")

    return parser.parse_args(args)


def main(args):
    args = parse_args(args)
    print(args)

    # folder with training directory (with training files) and experiment directory (with simulation outputs) inside.
    base_experiment_dir = args.experiment_dir + '/'

    # Fetch these from the command line at some point
    run_experiments = True          # if False only evaluation will done
    evaluation_on = False           # if False only simulation will run
    bulk_postprocessing_on = True   # If True first run simulation then run evaluation (after all simulation runs are
                                    # complete). If True run evaluation after each simulation run.
    # Setup of each experiment run
    experiment_runs = [
        ################################################################################################
        ################################################################################################
        #####################             Experiment             #######################################
        ################################################################################################
        ################################################################################################
        ## model 1 - process_model
        {"model_name":              "process_model",
         "agent_class":             GithubProcessAgent,
         "start_date":              "2021-04-01",  # simulation start date
         "end_date":                "2021-04-30",  # simulation end date, last day included
         "training_start_date":     "2021-03-01",
         "training_end_date":       "2021-03-31",
         "max_iterations":          100000,
         "repetitions":             1,
         # simulation output dir path:
         "output_dir":              base_experiment_dir,
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir,
         "training_file":           args.training,  # training
         "process_model":           args.process_model,  # training
         "initial_state_file":      args.initial_state, # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None},

        ################################################################################################
        ## model 2 - probabilistic_model
        {"model_name":              "probabilistic_model",
         "agent_class":             GithubProbabilisticAgent,
         "start_date":              "2021-04-01",  # simulation start date
         "end_date":                "2021-04-30",  # simulation end date, last day included
         "training_start_date":     "2021-03-01",
         "training_end_date":       "2021-03-31",
         "max_iterations":          100000,
         "repetitions":             1,
         # simulation output dir path:
         "output_dir":              base_experiment_dir,
         # training files and directory where training and initial state files are stored.:
         "training_dir":            base_experiment_dir,
         "training_file":           args.training,  # training
         "initial_state_file":      args.initial_state, # if file does not exist it will be created, otherwise initial state will be loaded from it.
         # ground truth # for evaluation only.
         "ground_truth_file":       None},
    ]
    
    run_batch(experiment_runs, run_experiments, evaluation_on)


if __name__ == "__main__":
    # Output is generated in the experiment directory (default location DASH_POSAM_ROOT / 'experiment_github'/ ) in
    # simulation_process_model.json file
    #
    # command line examples:
    # 1. run experiment using default arguments. Default training traces file DASH_POSAM_ROOT / 'experiment_github'/ training_traces.pickle ; Default petri net model file DASH_POSAM_ROOT / 'experiment_github'/ model.pickle
    # gh_process_experiment.py
    # 2. run experiment for './my_training_traces.pickle' and './my_model.pickle'
    # gh_process_experiment.py -t './my_training_traces.pickle' -m  './my_model.pickle'
    # 3. run experiment using default model and traces file names but in a different experiment directory:
    # gh_process_experiment.py -e './my_exp_dir'
    main(sys.argv[1:])

