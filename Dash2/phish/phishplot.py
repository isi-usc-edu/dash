from math import sqrt
import matplotlib.pyplot as plt
from Dash2.phish.phish_experiment import run_trials, get_args


# 'results' is currently a dict of {p(recognize): [mean num phish, median, std dev]}
def plot_results(results, title="", xlabel="", trials_per_cell=1):
    fig, ax = plt.subplots(1, 1)
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    #ax.set_xticks(record_names)  # assume these are years as integers
    ax.set(title=title)
    styles = ["o", "^", "s"]  # Can add other things here but this makes all the graph lines unique
    #for i, g_name in enumerate(graph_names):
    #    ax.plot(record_names, results[g_name], styles[i % len(styles)]+'-', label=g_name, markevery=1)
    ax.errorbar(sorted(results.keys()), [results[k][0] for k in sorted(results.keys())],
                [results[k][2] * 2 / sqrt(trials_per_cell) for k in sorted(results.keys())])  # 1 std dev up and down
    ax.set_ylabel('Number of phish')
    ax.set_xlabel(xlabel)
    plt.legend(loc="upper left")
    plt.show()
    print('done showing graph', title, xlabel)


if __name__ == "__main__":
    num_trials = 30
    max_num_rounds = 10
    # Vary probability of recognizing phish with fixed prob of clicking unrecognized phish or or forwarding
    if True:
        results = {p * 0.1: run_trials(num_trials, 'number', get_args(),
                                                        max_rounds=max_num_rounds,
                                                        num_workers=100,
                                              worker_fields={'probability_recognize_phish': p * 0.1,
                                                             'probability_click_unrecognized_phish': 0.5,
                                                             'forward_probability': {'leisure': 0.1, 'work': 0.1}})
                   for p in range(1, 10)}
        plot_results(results, title="Number of phish opened as probability of recognizing phish increases",
                     xlabel="Probability of recognizing phish", trials_per_cell=num_trials)
    # vary probability of forwarding unrecognized phish with fixed prob of recognizing and clicking
    if True:
        results = {p * 0.1: run_trials(num_trials, 'number', get_args(),
                                                        max_rounds=max_num_rounds,
                                                        num_workers=100,
                                                        worker_fields={'probability_recognize_phish': 0.6,
                                                                       'probability_click_unrecognized_phish': 0.5,
                                                                       'forward_probability':
                                                                        {'leisure': p * 0.1, 'work': p * 0.1},
                                                                       'number_forwarding_recipients': 1})
                   for p in range(1, 10)}
        plot_results(results, title="Number of phish opened as probability of forwarding email increases",
                     xlabel="Probability of forwarding messages", trials_per_cell=num_trials)
    print(str(num_trials) + " trials run, max_rounds = " + str(max_num_rounds))
    print(results)
