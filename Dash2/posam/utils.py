import sys; sys.path.extend(['../../'])
import pandas as pd
import time
from datetime import datetime
import json
import pickle
import random
import os

SECONDS_IN_DAY = 24 * 3600

aliases = {"rootID": "r",
           "nodeID": "n",
           "platform": "p",
           "informationID": "i",
           "nodeTime": "t",
           "parentID": "c",
           "actionType": "a",
           "nodeUserID": "u",
           "parentUserID": "x",
           "rootUserID": "z"
           }

def count_days(start_date, end_date, end_date_included = True):
    if isinstance(start_date, float) and isinstance(end_date, float) or \
            isinstance(start_date, int) and isinstance(end_date, int):
        number_of_days_in_simulation = 1.0 + float(end_date - start_date) / float(SECONDS_IN_DAY)
    else:
        number_of_days_in_simulation = 1.0 + float((time.mktime(datetime.strptime(str(end_date) + ' 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())
                                            - time.mktime(datetime.strptime(str(start_date) + ' 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())) / (3600.0 * 24.0))
    number_of_days_in_simulation = number_of_days_in_simulation if end_date_included else number_of_days_in_simulation - 1.0
    return number_of_days_in_simulation


def random_pick_prob(prob, data):
    """
    Returns random item using provided distribution prob.

    :param data:
    :param prob:
    :return:
    """
    if len(data) == 1:
        return data[0], 0
    elif len(data) == 0:
        return None, None
    choice = random.uniform(0, 1)
    cumulative_probability = 0.0
    res = None
    index = 0
    for item, item_probability in zip(data, prob):
        cumulative_probability += item_probability
        if choice < cumulative_probability:
            res = item
            break
        index += 1
    return res, index


def random_pick(prob_dict):
    """
    Returns random item using provided distribution prob.

    :param data:
    :param prob:
    :return:
    """
    data = []
    prob = []
    for k, v in prob_dict.items():
        data.append(k)
        prob.append(v)

    if data is None or prob is None:
        raise ValueError('Data and probabilities should not be None objects')

    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    res = None
    for item, item_probability in zip(data, prob):
        cumulative_probability += item_probability
        if x < cumulative_probability:
            res = item
            break
    return res


def load_data(filepath, ignore_first_line=True, name_mappings=None, verbose=False, short=False, aliases=None):
    """
    Description: Loads a dataset from a json file and converts date/time to numerical values.

    Input:
        :filepath: (str) The filepath to the submission file.
        :name_mappings: (dict) A dictionary where the keys are existing names
            and the values are new names to replace the existing names.

    Output:
        :dataset: (pandas dataframe) The loaded dataframe object.
    """
    dataset = load_json_into_df(filepath, ignore_first_line, verbose, short, aliases)
    dataset = convert_datetime(dataset, verbose)
    return dataset


def load_json_into_df(filepath, ignore_first_line, verbose, short, aliases=None):
    """
    Description: Loads a dataset from a json file.

    Input:
        :filepath: (str) The filepath to the submission file.
        :ignore_first_line: (bool) A True/False value. If True the first line
            is skipped.

    Output:
        :dataset: (pandas dataframe) The loaded dataframe object.
    """

    dataset = []

    if verbose:
        print('Loading dataset at ' + filepath)

    with open(filepath, 'r') as file:
        for line_number, line in enumerate(file):

            if (line_number == 0 and ignore_first_line) or line == "" or line is None or line == "\n":
                continue

            if verbose:
                print(line_number)
                print('\r')

            line_data = json.loads(line)
            if line_data['nodeUserID'] is not None:
                if aliases is not None:
                    line_data = {k: v for k, v in line_data.items() if k in aliases.keys()}
                    for k, alias in aliases.items():
                        k_val = line_data[k]
                        line_data.pop(k)
                        line_data[alias] = k_val
                dataset.append(line_data)

                if short:
                    if len(dataset) == 1000:
                        break

    if verbose:
        print(' ' * 100)
        print('\r')
        print(line_number)

    dataset = pd.DataFrame(dataset)

    if aliases is not None:
        inverse = {v:k for k, v in aliases.items()}
        new_columns = dataset.columns.values
        new_columns = [inverse[c] for c in new_columns]
        dataset.columns = new_columns

    return dataset


def convert_datetime(dataset, verbose):

    node_time_field_name = 'nodeTime'

    if verbose:
        print('Converting strings to datetime objects...')

    try:
        dataset[node_time_field_name] = pd.to_datetime(dataset[node_time_field_name], unit='s',utc=True)
    except:
        try:
            dataset[node_time_field_name] = pd.to_datetime(dataset[node_time_field_name], unit='ms',utc=True)
        except:
            dataset[node_time_field_name] = pd.to_datetime(dataset[node_time_field_name], utc=True)

    dataset[node_time_field_name] = dataset[node_time_field_name].dt.tz_localize(None)
    dataset[node_time_field_name] = dataset.apply(lambda row: int(row[node_time_field_name].timestamp()), axis=1)

    if verbose:
        print(' Done')

    return dataset


def convert_json_into_df(filepath, ignore_first_line=False):
    """
    Description: Convert json event log into pandas dataframe in pickle format.

    Input:
        :filepath: (str) The filepath to the submission event log.
    """

    dataset = []
    with open(filepath, 'r') as file:
        for line_number, line in enumerate(file):
            if (line_number == 0 and ignore_first_line) or line == "" or line is None or line == "\n":
                continue
            line_data = json.loads(line)
            dataset.append(line_data)
    dataset_df = pd.DataFrame(dataset)

    output_filepath = str(filepath).replace('.json', '.pickle')
    with open(output_filepath, 'wb') as o_file:
        pickle.dump(dataset_df, o_file)

