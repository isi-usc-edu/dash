import sys; sys.path.extend(['.;../../'])
import os
import pickle
import time
from matplotlib import pyplot as plt
from zipfile import ZipFile
from Dash2.posam.create_initial_state import trim_training_interval
from Dash2.posam.utils import  SECONDS_IN_DAY
from datetime import  datetime
import pandas as pd
import argparse
from pathlib import Path


DASH_POSAM_ROOT=Path('.')

def plot_activity_over_time(gt_traces_path, sim_process_traces_path, sim_prob_traces_path):
    """
    Print charts.
    """
    start_time = time.mktime(datetime.strptime("2021-04-01" + ' 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())
    end_time = time.mktime(datetime.strptime("2021-04-30" + ' 23:59:59', "%Y-%m-%d %H:%M:%S").timetuple())
    # load gt
    # unzip training traces if in .zip
    if os.path.exists(gt_traces_path) and str(gt_traces_path).find('.zip') != -1:
        with ZipFile(gt_traces_path, 'r') as zip:
            gt_traces_path = str(gt_traces_path).replace('.zip', '.pickle')
            traces_filename = gt_traces_path.split('/')[-1]
            zip.extract(traces_filename, path=gt_traces_path.replace(traces_filename, ''))

    with open(gt_traces_path, 'rb') as f:
        traces_df = pickle.load(f)
    gt_traces_df = trim_training_interval(traces_df, start_time, end_time)

    # load simulation
    with open(sim_process_traces_path, 'rb') as f:
        sim_process_traces_df = pickle.load(f)
    with open(sim_prob_traces_path, 'rb') as f:
        sim_prob_traces_df = pickle.load(f)

    # over time activity
    df_names = {"GT": gt_traces_df, "Process model": sim_process_traces_df, "Probabilistic model": sim_prob_traces_df}
    to_concat = list()
    for df_name, df in df_names.items():
        print(df_name)
        if df_name == 'GT':
            df['time:timestamp'] = df.apply(lambda row: int(row['time']), axis=1)
        df['day'] = df.apply(lambda row: int(int(row['time:timestamp']) / int(SECONDS_IN_DAY)) , axis=1)
        min_day = df['day'].min()
        df['day'] = df.apply(lambda row: int(int(row['day']) - min_day + 1), axis=1)
        events_per_day = df.groupby(['day']).size()
        events_per_day = events_per_day.rename(df_name)
        to_concat.append(events_per_day)
        print(events_per_day.sum())

    df = pd.concat(to_concat, axis=1)
    df.plot.line()
    #plt.savefig('eval.png', dpi=200)
    plt.show()


def parse_args(args):
    parser = argparse.ArgumentParser(description="VENOM Demo for July 2021 Hackathon")

    parser.add_argument("--ground_truth", "-gt",
                        type=str,
                        required=False,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'training_traces.zip',
                        help="Training traces file name. Format: pickled pandas dataframe.")

    parser.add_argument("--sim_process", "-s1",
                        type=str,
                        required=False,
                        default=DASH_POSAM_ROOT / 'experiment_github' / 'simulation_process_model.pickle',
                        help="Process-driven simulation pickled dataframe.")

    parser.add_argument("--sim_probabilistic", "-s2",
                        type=str,
                        required=False,
                        default=str(DASH_POSAM_ROOT / 'experiment_github' / 'simulation_process_model_05w.pickle'),
                        help="Probabilistic simulation pickled dataframe.")

    return parser.parse_args(args)


def main(args):
    args = parse_args(args)
    print(args)
    plot_activity_over_time(gt_traces_path=args.ground_truth, sim_process_traces_path=args.sim_process, sim_prob_traces_path=args.sim_probabilistic)



if __name__ == "__main__":
    # Command line example:
    # 1. Run without arguments, use default param values
    # evaluate.py
    main(sys.argv[1:])

