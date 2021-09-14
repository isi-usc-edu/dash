# Uses the mailReader.py agent and the Tutorial mail_hub to create an experiment with n agents
# reading and sending mail, with known email addresses, and k attacker agents sending phish.
# Based on nurse_experiment.py (probably should extract a reusable test harness from this).
from random import sample

from Dash2.phish.mailReader import MailReader
import random
import numpy
import argparse

from datetime import datetime

# These are upper and lower bounds on uniform probability distributions used to select parameters for agents.
BIG_5_LOWER = 0.2  # The 'big 5' personality traits of extraversion, agreeableness, conscientiousness,
BIG_5_UPPER = 0.9  # openness and emotional stability (usually called neuroticism) are all controlled by these bounds
REPLY_LOWER = 0  # Not currently used
REPLY_UPPER = 0.8
WORK_REPLY_LOWER = 0  # Set here but not used in the agent
WORK_REPLY_UPPER = 0.8
LEISURE_FWD_LOWER = 0  # Set here but not used in the agent
LEISURE_FWD_UPPER = 0.8


def trial(objective, args, num_workers=1, num_recipients=4, num_phishers=1,  # num_workers was 20
          phish_targets=1, max_rounds=20, worker_fields=[]):  # phish_targets was 20

    workers = []
    domain = '@amail.com'
    for i in range(0, num_workers):
        w = MailReader('mailagent' + str(i + 1) + domain, args)
        workers.append(w)
        choose_gender_personality(w)
        choose_recipients(w, i, num_workers, num_recipients, domain=domain)
        # Allow setting worker fields programmatically
        for field in worker_fields:
            setattr(w, field, worker_fields[field])
        w.traceLoop = False

    phisher = MailReader('phisher@bmail.com', args)
    choose_victims(phisher, phish_targets, num_workers, domain=domain)
    print('phisher mail stack length', len(phisher.mail_stack))
    phisher.active = True
    phisher.traceLoop = False
    phisher.trace_client = False

    # Used as an objective
    phished = False
    phish_start_time = datetime.now()
    phish_end_time = datetime.now()

    # dovetail the worker and phisher agents until they're all finished
    finished_workers = set()
    iteration = 1
    total_mail_stack = 0
    total_mails_read = 0
    total_mails_sent = 0
    last_mails_sent = 0
    last_mails_read = 0
    last_mail_stack = 0
    generations_since_change = 0

    while len(workers) > len(finished_workers) and iteration <= max_rounds and generations_since_change < 4:
        #total_mail_stack = 0  # I'm not sure why these were zeroed on each round
        #total_mails_read = 0
        #total_mails_sent = 0
        for w in workers:
            if w not in finished_workers:
                next_action = w.agent_loop(max_iterations=1, disconnect_at_end=False)  # don't disconnect since will run again

                if (not phished) and (len(w.attachments_opened) > 0) and (w.attachments_opened.__contains__("phish.xlsx")):
                    phished = True
                    phish_end_time = iteration  # datetime.now() we should use the iteration, not real-time, here

                # Should these really be added each iteration? Each agent stores them across iterations.
                total_mail_stack += len(w.mail_stack)
                total_mails_read += w.mails_read
                total_mails_sent += w.mails_sent
                if next_action is None:
                    finished_workers.add(w)
        if phisher.active:
            next_action = phisher.agent_loop(max_iterations=1, disconnect_at_end=False)  # don't disconnect since will run again
            # total_mail_stack += len(phisher.mail_stack)
            # total_mails_read += phisher.mails_read
            # total_mails_sent += phisher.mails_sent
            if next_action is None:
                phisher.active = False
        if total_mail_stack == last_mail_stack and total_mails_read == last_mails_read and total_mails_sent == last_mails_sent:
            generations_since_change += 1
        else:
            generations_since_change = 0
        #print('round', iteration, 'total stack', total_mail_stack, 'total read', total_mails_read,
        #      'total_sent', total_mails_sent, 'generations since change:', generations_since_change)
        last_mail_stack = total_mail_stack
        last_mails_sent = total_mails_sent
        last_mails_read = total_mails_read
        iteration += 1

    for w in workers:
        w.disconnect()

    # Print some statistics about the run
    #print('worker, number of emails received, sent, phish identified, attachments opened:')
    #for w in workers:
    #    print(w.address, w.mails_read, w.mails_sent, len(w.phish_identified), w.attachments_opened)
    #print('phisher:', phisher.address, phisher.mails_sent, phisher.phish_identified, phisher.attachments_opened)

    if objective == 'number':
        phish_attachments_opened = []
        for w in workers:
            worker_attachments_opened = 0
            for attachment in w.attachments_opened:
                if attachment == "phish.xlsx":
                    worker_attachments_opened += 1
            phish_attachments_opened.append(worker_attachments_opened)
        print(sum(phish_attachments_opened), 'phish attachments opened:')
        return sum(phish_attachments_opened)  # Was average opened per worker, now returning the total number opened
    elif objective == 'time':
        if phished:
            return (phish_end_time-phish_start_time).total_seconds()
        else:
            return -1


def choose_recipients(agent, worker_i, num_workers, num_recipients, domain='@amail.com'):
    # reset recipients
    for key in agent.colleagues:
        agent.colleagues[key] = []
    recipients = sample([i for i in range(0, num_workers) if i != worker_i], num_recipients)
    mode_options = ['leisure', 'work']

    stack = []
    for i in range(0, num_recipients):
        address = 'mailagent' + str(recipients[i] + 1) + domain
        mode = random.choice(mode_options)
        mail = {'to': address,
                'subject': 'test',
                'mode': mode,
                'body': 'this is a test message ' + str(i+1) + ' for ' + address,
                'attachment': 'budget.xlsx' if mode == 'work' else 'kittens.jpeg'}
        agent.colleagues[mode].append(address)
        stack.append(mail)
    agent.mail_stack = stack


def choose_victims(phisher, num_victims, num_workers, domain='@amail.com'):
    # reset victims
    for key in phisher.colleagues:
        phisher.colleagues[key] = []
    victims = sample(list(range(0, num_workers)), num_victims)
    mode_options = ['leisure', 'work']

    stack = []
    for i in range(0, num_victims):
        address = 'mailagent' + str(victims[i] + 1) + domain
        mode = random.choice(mode_options)
        mail = {'to': address,
                'subject': 'test',
                'mode': mode,
                'body': 'this is a test message for ' + address,
                'attachment': 'phish.xlsx'}
        phisher.colleagues[mode].append(address)
        stack.append(mail)
    phisher.mail_stack = stack


def choose_gender_personality(worker):
    genders = ['Male', 'Female']
    worker.gender = random.choice(genders)
    worker.extraversion = random.uniform(BIG_5_LOWER, BIG_5_UPPER)
    worker.agreeableness = random.uniform(BIG_5_LOWER, BIG_5_UPPER)
    worker.conscientiousness = random.uniform(BIG_5_LOWER, BIG_5_UPPER)
    worker.emotional_stability = random.uniform(BIG_5_LOWER, BIG_5_UPPER)
    worker.openness = random.uniform(BIG_5_LOWER, BIG_5_UPPER)
    worker.leisure_forward_probability = random.uniform(LEISURE_FWD_LOWER, LEISURE_FWD_UPPER)
    worker.work_reply_probability = random.uniform(WORK_REPLY_LOWER, WORK_REPLY_UPPER)


def run_trials(num_trials, objective, args, num_workers=50, num_recipients=10,  # num_workers was 100, num_recipients was 4
               num_phishers=1, phish_targets=15, max_rounds=20, worker_fields=[]):  # phish_targets was 20
    output = []
    for _ in range(num_trials):
        trial_output = trial(objective, args, num_workers, num_recipients, num_phishers, phish_targets, max_rounds,
                             worker_fields=worker_fields)
        if trial_output == -1:
            continue  # no phish has occured -> ignore
        output.append(trial_output)

    if len(output) == 0:
        return None
    print('final trial output:', output)
    if objective == 'number':
        print('Number of attachments opened with', num_recipients, 'recipients: mean:', numpy.mean(output), \
            'median:', numpy.median(output), 'standard deviation:', numpy.std(output))
    return [numpy.mean(output), numpy.median(output), numpy.std(output)]


def get_args():
    parser = argparse.ArgumentParser(description='Create mail reader config.')
    parser.add_argument(
        '--use-mailserver', dest='use_mailserver', default=False,
        action='store_const', const=True, help='Use mail server to send emails'
    )
    parser.add_argument(
        '--project-name', type=str, dest='project_name',
        help='Specify DETER project name'
    )
    parser.add_argument(
        '--experiment-name', type=str, dest='experiment_name',
        help='Specify DETER experiment name'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    # Run it once
    # trial()
    num_trials = 10
    max_num_rounds = 10
    print(run_trials(num_trials, 'number', args, max_rounds=max_num_rounds))
    print(str(num_trials) + " trials run, max_rounds = " + str(max_num_rounds))
