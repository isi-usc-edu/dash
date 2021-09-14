import sys; sys.path.extend(['../../'])
import csv
from datetime import datetime
import random
import numpy
import time
import bisect
import json
import _pickle as pickle

# depricated, do not use
event_types = ["CreateEvent", "DeleteEvent", "PullRequestEvent", "PullRequestReviewCommentEvent", "IssuesEvent",
               "IssueCommentEvent", "PushEvent", "CommitCommentEvent","WatchEvent", "ForkEvent", "GollumEvent",
               "PublicEvent", "ReleaseEvent", "MemberEvent", "CreateEvent/new"]
event_types_indexes = {"CreateEvent":0, "DeleteEvent":1, "PullRequestEvent":2, "PullRequestReviewCommentEvent":3,
                       "IssuesEvent":4, "IssueCommentEvent":5, "PushEvent":6, "CommitCommentEvent":7, "WatchEvent":8,
                       "ForkEvent":9, "GollumEvent":10, "PublicEvent":11, "ReleaseEvent":12, "MemberEvent":13, "CreateEvent/new": 14}


def merge_log_file(file_names, output_file_name, header_line=None, sort_chronologically=False):
    if len(file_names) == 1: # no need to merege or to sort
        pass
    if sort_chronologically:
        output_file = open(output_file_name, 'w')
        if header_line is not None:
            output_file.write(header_line)
            output_file.write("\n")

        input_logs = []
        lines = []
        for filename in file_names:
            input_logs.append(open(filename, "r"))
            lines.append(None)

        while _refill_lines(input_logs, lines):
            line = _retreive_earliest_event(lines)
            output_file.write(line)

        for input_log in input_logs:
            input_log.close()
        output_file.close()
    else:
        output_file = open(output_file_name, 'w')
        if header_line is not None:
            output_file.write(header_line)
            output_file.write("\n")

        for filename in file_names:
            input_log = open(filename, "r")
            datareader = input_log.readlines()
            for line in datareader:
                output_file.write(line)
            input_log.close()
        output_file.close()


'''
Returns True if array of lines contains non empty string
'''


def _refill_lines(input_logs, lines):
    res = False
    for index in range(0, len(lines), 1):
        if lines[index] is None:
            lines[index] = input_logs[index].readline()
            if lines[index] != "":
                res = True
        else:
            if lines[index] != "":
                res = True
    return res


'''
Returns earliest event from list of event lines
'''


def _retreive_earliest_event(lines):
    earliest_event_line = None
    earliest_event_time = None
    earliest_event_index = None
    for index in range(0, len(lines), 1):
        if lines[index] is not None and lines[index] != "":
            row = lines[index].split(',')
            event_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            if earliest_event_line is None:
                earliest_event_line = lines[index]
                earliest_event_time = event_time
                earliest_event_index = index
            if earliest_event_time > event_time:
                earliest_event_time = event_time
                earliest_event_line = lines[index]
                earliest_event_index = index
    # remove earliest event from the list of events
    if earliest_event_index is not None:
        lines[earliest_event_index] = None

    return earliest_event_line


def load_id_dictionary(dictionary_file_name, isSimId2strId = True):
    dict_file = open(dictionary_file_name, "r")
    datareader = csv.reader(dict_file)
    ids_map = {}
    counter = 0
    for row in datareader:
        if counter != 0:
            src_id = row[0]
            target_id = row[1]
            if isSimId2strId:
                ids_map[int(target_id)] = src_id
            else:
                ids_map[src_id] = int(target_id)
        counter += 1
    dict_file.close()
    return ids_map


def translate_user_and_repo_ids_in_event_log(even_log_file, output_file_name, users_ids_file, repos_ids_file):
    input_file = open(even_log_file, 'r')
    output_file = open(output_file_name, 'w')
    users_map = load_id_dictionary(users_ids_file)
    repos_map = load_id_dictionary(repos_ids_file)

    datareader = csv.reader(input_file)
    for row in datareader:
        user_id = int(row[2])
        repo_id = int(row[3])
        if users_map.has_key(user_id):
            src_user_id = users_map[user_id]
        else:
            src_user_id = user_id
        if repos_map.has_key(repo_id):
            src_repo_id = repos_map[repo_id]
        else:
            src_repo_id = repo_id
        output_file.write(row[0])
        output_file.write(",")
        output_file.write(row[1])
        output_file.write(",")
        output_file.write(str(src_user_id))
        output_file.write(",")
        output_file.write(str(src_repo_id))
        output_file.write("\n")

    input_file.close()
    output_file.close()


def convert_pickle_to_json(events_file, output_file_name, team_name, scenario, domain, platform):
    input_file = open(events_file, 'r')
    output_file = open(output_file_name, 'w')

    output_file.write("{\"team\" : \"" + str(team_name) + "\", \"scenario\" : " + str(scenario) +
                ", \"domain\" : \"" + str(domain) + "\", \"platform\" : \"" + str(platform) + "\", \"data\" : " + "[")
    first_item = True
    while True:
        try:
            event_json = pickle.load(input_file)
            if not first_item:
                output_file.write(", \n")
            json.dump(event_json, output_file)
            first_item = False
        except EOFError:
            break
    output_file.write("]}")

    input_file.close()
    output_file.close()


def remove_owner_id_from_repos_in_event_log(even_log_file, output_file_name):
    input_file = open(even_log_file, 'r')
    output_file = open(output_file_name, 'w')

    datareader = csv.reader(input_file)
    for row in datareader:
        if row[0] != "timestamp":
            #output_file.write(str(row[0]).replace("2016-03", "2016-01"))
            output_file.write(row[0])
            output_file.write(",")
            output_file.write(row[1])
            output_file.write(",")
            output_file.write(row[2])
            output_file.write(",")
            output_file.write(str(row[3]).split("/")[1])
            #output_file.write(row[3])
            output_file.write("\n")

    input_file.close()
    output_file.close()


def split_event_log_by_month(even_log_file, output_file_name, prefix):
    input_file = open(even_log_file, 'r')
    output_file = open(output_file_name, 'w')

    datareader = csv.reader(input_file)
    for row in datareader:
        if row[0] != "timestamp":
            if not str(row[0]).startswith(prefix):
                output_file.close()
                prefix = str(row[0])[0:7]
                output_file = open(output_file_name + prefix, 'w')
            output_file.write(row[0])
            output_file.write(",")
            output_file.write(row[1])
            output_file.write(",")
            output_file.write(row[2])
            output_file.write(",")
            output_file.write(row[3])
            output_file.write("\n")

    input_file.close()
    output_file.close()


def collect_unique_user_event_pairs(even_log_file, UstrId2UsimId=None):
    input_file = open(even_log_file, 'r')
    unique_events = set()

    datareader = csv.reader(input_file)
    for row in datareader:
        if row[0] != "timestamp":
            event = row[1]
            user = row[2]
            unique_events.add((user, event))
    print("unique events ", len(unique_events))
    input_file.close()

    if UstrId2UsimId is not None:
        event2users = {k : [] for k in event_types}
        for user, event in unique_events:
            event2users[event].append(UstrId2UsimId[user])
        return event2users


def random_pick_sorted(sorted_data, cumulative_sorted_prob):
    if sorted_data is None or cumulative_sorted_prob is None:
        raise ValueError('Data and probabilities should not be None objects')

    x = random.uniform(0, 1)
    index = bisect.bisect(cumulative_sorted_prob, x)
    if index >= len(sorted_data):
        index -= 1
    return sorted_data[index]


def random_pick_notsorted(data, prob):
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


def sort_data_and_prob_to_cumulative_array(data, probabilities):
    # sort probabilities and zip with data
    if data is None or probabilities is None:
        raise ValueError('Data and probabilities should not be None objects')

    sorted_prob = [(k, v) for k, v in zip(probabilities, data)]
    sorted_prob = sorted(sorted_prob, key=lambda tup: tup[0], reverse=True)
    sorted_data = [v for k, v in sorted_prob]
    sorted_prob = [k for k, v in sorted_prob]
    # make probabilities cumulative
    prob_sum = 0.0
    max_index = len(sorted_prob)
    for index in range(0, max_index, 1):
        prob_sum += sorted_prob[index]
        sorted_prob[index] = prob_sum

    return sorted_data, sorted_prob


def random_pick_numpy(objects_to_pick, probabilities):
    res = numpy.random.choice(objects_to_pick, replace=False, p=probabilities)
    return res


def test_random_pick():
    data = []
    probabilities = []
    number_of_items = 5
    number_of_iterations_in_test = 1000000

    prob_sum = 0.0
    for index in range(0, number_of_items, 1):
        data.append(random.uniform(0, 1))
        probabilities.append(random.uniform(0, 1))
        prob_sum += probabilities[index]
    probabilities = [k / prob_sum for k in probabilities]

    # sort probabilities zip with data
    sorted_data, sorted_prob = sort_data_and_prob_to_cumulative_array(data, probabilities)

    ##########

    start_time = time.time()
    for index in range(0, number_of_iterations_in_test, 1):
        random_pick_sorted(sorted_data, sorted_prob)
        if index % 10000 == 0:
            print("iteration: ", index)
    end_time = time.time()
    print("Time (random_pick_sorted): ", end_time - start_time)

    start_time = time.time()
    for index in range(0, number_of_iterations_in_test, 1):
        random_pick_numpy(data, probabilities)
        if index % 10000 == 0:
            print("iteration: ", index)

    end_time = time.time()
    print("Time (random_pick_numpy): ", end_time - start_time)


if __name__ == "__main__":
    #collect_unique_user_event_pairs(sys.argv[1])
    test_random_pick()
