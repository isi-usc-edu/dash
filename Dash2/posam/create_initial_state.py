import sys; sys.path.extend(['.;../../'])
import os
import collections
import socket
import json
import time
import pickle
import argparse
import random
from pathlib import Path
from zipfile import ZipFile
from datetime import  datetime
from Dash2.posam.utils import count_days

# DASH root path, currently not used
DASH_ROOT=Path('./Dash2')
# path to data folder with inputs and outputs for the simulation
DASH_POSAM_ROOT=Path('./Dash2/posam/data')


def create_initial_state_process_mapping(training_data_path, initial_state_path, process_model=None, **kwargs):
    with open(training_data_path, 'rb') as f:
        traces_df = pickle.load(f)

    with open(process_model, 'rb') as f:
        p_net_model = pickle.load(f)

    transitions_mapping = dict()
    for t in p_net_model.transitions:
        if t.label is not None:
            print(t)
            transitions_mapping[t.label] = dict()

    traces_gr = traces_df.groupby(['case:concept:name'])
    for trace_id, traces in traces_gr:
        traces = traces.sort_values('time:timestamp')
        traces = traces.to_dict('records')
        for event in traces:
            transition_name = event['concept:name']
            if transition_name in transitions_mapping:
                if trace_id not in transitions_mapping[transition_name]:
                    transitions_mapping[transition_name][trace_id] = list()
                transitions_mapping[transition_name][trace_id].append(event)

    initial_state_process_mapping = {"model": p_net_model,
                                     "traces": traces_df,
                                     "transitions_mapping":transitions_mapping}

    with open(initial_state_path, 'wb') as f:
        pickle.dump(initial_state_process_mapping, f)

    return initial_state_process_mapping


########################################################################################################################
# Utility initial state / queries
########################################################################################################################

def load_last_event_time(p_dataset, users):
    """
    Returns last event time for each user id.
    :param dataset:
    :param users - input/output dictionary of users.
    :return: None but users dictionary is updated
    """
    p_dataset = p_dataset.drop_duplicates(subset=['org:resource', 'time:timestamp'], keep='last')
    user_last_event_time = p_dataset.groupby(['org:resource'])['time:timestamp'].max()

    for user_id, t in user_last_event_time.items():
        users[user_id]['last_event_time'] = time.mktime(t.timetuple())


def load_event_rates(p_dataset, number_days_in_training, users):
    """
    Returns event rates for each user id.
    """
    min_time = p_dataset['time'].min()
    max_time = p_dataset['time'].max()
    p_dataset['time2'] = p_dataset.apply(lambda row: row['time'] - min_time, axis=1)
    interval_length = max_time - min_time

    p_dataset = p_dataset.drop_duplicates(subset=['org:resource', 'time2', 'time'], keep='last')
    n_days_in_training = number_days_in_training
    user_activity_freqs = p_dataset.groupby(['org:resource']).size().apply(lambda x: float(x) / float(n_days_in_training))
    user_events = p_dataset.groupby(['org:resource'])

    for user_id, event_rate in user_activity_freqs.items():
        users[user_id]['event_rate'] = event_rate
        users[user_id]['time_intervals'] = list()

    counter = 0
    for user_id, u_events in user_events:
        counter += 1
        if counter % 1000 == 0:
            print("Users processed: " + str(counter))
        for row_index, row in u_events.iterrows():
            users[user_id]['time_intervals'].append(row['time'])
        if len(users[user_id]['time_intervals']) > 0:
            users[user_id]['time_intervals'].sort()
            users[user_id]['time_intervals'] = [t if index == 0 else t - users[user_id]['time_intervals'][index - 1]
                                                for index, t in enumerate(users[user_id]['time_intervals']) ]
            last_interval = interval_length - sum(users[user_id]['time_intervals'])
            users[user_id]['time_intervals'][0] += last_interval


def load_action_type_probabilities(p_dataset, users):
    """
    :param dataset:
    :param users - input/output dictionary of users
    :return:
    """
    print("Total events: " + str(len(p_dataset)))
    event_types = list(p_dataset['concept:name'].unique())

    user_events = p_dataset.groupby(['org:resource', 'concept:name']).size()
    events_total_count = user_events.groupby(['org:resource']).sum()

    for index, freq in user_events.items():
        user_id = index[0]
        event = index[1]
        if 'event_prob' not in users[user_id]:
            users[user_id]['event_prob'] = {event_type: 0.0 for event_type in event_types}
        total_event_count = events_total_count[user_id]
        assert freq <= total_event_count
        users[user_id]['event_prob'][event] = float(freq) / float(total_event_count)


def load_past_traces_prob(p_dataset, users):
    """
    :param dataset:
    :param users - input/output dictionary of users
    :return:
    """
    user_events = p_dataset.groupby(['org:resource'])
    for user_id, events in user_events:
        users[user_id]['traces'] = events.reset_index()
        users[user_id]['prob_new_issue'] = random.uniform(0.1, 0.2)
        users[user_id]['t_index'] = 0


def load_issue_probabilities(p_dataset, users):
    """
    :param dataset:
    :param users - input/output dictionary of users
    :return:
    """
    user_events = p_dataset.groupby(['org:resource', 'case:concept:name']).size()
    events_total_count = user_events.groupby(['org:resource']).sum()

    for index, freq in user_events.items():
        user_id = index[0]
        issue_id = index[1]
        if 'issue_prob' not in users[user_id]:
            users[user_id]['issue_prob'] = dict()
        total_event_count = events_total_count[user_id]
        assert freq <= total_event_count
        users[user_id]['issue_prob'][issue_id] = float(freq) / float(total_event_count)


def trim_training_interval(p_dataset, start_time, end_time):
    """
    Returns trimmed dataset
    """

    p_dataset['time'] = p_dataset.apply(lambda row: time.mktime(row['time:timestamp'].timetuple()), axis=1)
    p_dataset = p_dataset[p_dataset['time'] >= start_time]
    p_dataset = p_dataset[p_dataset['time'] < end_time]
    return p_dataset


########################################################################################################################
# Load initial state for probabilistic and process-driven agents
########################################################################################################################

def create_initial_state(training_data_path, initial_state_path, process_model=None, **kwargs):
    # make sure full path and relative filenames are handled properly
    if os.path.exists(training_data_path):
        pass
    elif os.path.exists(Path(kwargs["training_dir"], kwargs["training_file"])):
        training_data_path = str(Path(kwargs["training_dir"], kwargs["training_file"]))
    else:
        raise ValueError("'training_file' parameter has unexpected value: " + training_data_path)
    if str(initial_state_path).find('/') != -1:
        initial_state_path = str(Path(kwargs["training_dir"], kwargs["initial_state_file"]))

    # unzip training traces
    if os.path.exists(training_data_path) and str(training_data_path).find('.zip') != -1:
        with ZipFile(training_data_path, 'r') as zip:
            training_data_path = str(training_data_path).replace('.zip', '.pickle')
            traces_filename = training_data_path.split('/')[-1]
            zip.extract(traces_filename, path=training_data_path.replace(traces_filename, ''))
    # unzip initial state
    if os.path.exists(initial_state_path) and str(initial_state_path).find('.zip') != -1:
        with ZipFile(initial_state_path, 'r') as zip:
            initial_state_path = str(initial_state_path).replace('.zip', '.pickle')
            initial_state_filename = initial_state_path.split('/')[-1]
            zip.extract(initial_state_filename, path=initial_state_path.replace(initial_state_filename, ''))

    with open(training_data_path, 'rb') as f:
        traces_df = pickle.load(f)
    # basic stats for probabilistic agent
    start_time = time.mktime(datetime.strptime(kwargs['training_start_date'] + ' 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())
    end_time = time.mktime(datetime.strptime(kwargs['training_end_date'] + ' 23:59:59', "%Y-%m-%d %H:%M:%S").timetuple())
    traces_df = trim_training_interval(traces_df, start_time, end_time)

    agents_data = {id: {'id': id, "roles": ["developer", "reviewer"], 'last_event_time': 1588313400.0, 'events': list()}
                   for id in list(traces_df['org:resource'].unique()) if id is not None}
    load_last_event_time(traces_df, agents_data)
    number_of_days_in_training = count_days(start_time, end_time, False)
    load_event_rates(traces_df, number_of_days_in_training, agents_data)
    load_action_type_probabilities(traces_df, agents_data)
    load_issue_probabilities(traces_df, agents_data)
    load_past_traces_prob(traces_df, agents_data)

    return agents_data


def main(args):
    parser = argparse.ArgumentParser(description="VENOM Demo for July 2021 Hackathon")
    parser.add_argument("--training", "-t",
                        type=str,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'training_traces.pickle',
                        help="Training traces file name. Format: pickled pandas dataframe.")

    parser.add_argument("--initial_state", "-s",
                        type=str,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'initial_state.pickle',
                        help="Initial state file (python pickled object).")

    parser.add_argument("--process_model", "-m",
                        type=str,
                        default=str(DASH_POSAM_ROOT / 'experiment_github' / 'model.pickle'),
                        help="Path to petri net process model (in pickle format).")

    args = parser.parse_args(args)
    print(args)

    create_initial_state_process_mapping(args.training, args.initial_state, process_model=args.process_model)


if __name__ == "__main__":
    # command line examples:
    # 1. create initial state using default arguments. Default training traces file DASH_POSAM_ROOT / 'experiment_github'/ training_traces.pickle ; Default petri net model file DASH_POSAM_ROOT / 'experiment_github'/ model.pickle
    # create_initial_state.py
    # 2. create initial state for './my_training_traces.pickle' and './my_model.pickle'
    # create_initial_state.py -t './my_training_traces.pickle' -m  './my_model.pickle'
    main(sys.argv[1:])
