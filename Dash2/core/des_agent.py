SECONDS_IN_DAY = 24 * 3600

import json
import pickle
from Dash2.core.string_aux import convert_camel

class DESAgent(object):
    """
    The DESAgent discrete event simulation agent.
    DES agent API includes these methods
    - agent_loop(self, **kwargs)
    - agent_decision_cycle(self, **kwargs)
    - next_event_time(self, **kwargs)
    """

    def __init__(self, **kwargs):
        self.hub = kwargs.get("hub", None)
        self.log_file = kwargs.get("log_file", None)
        if self.log_file is None and self.hub is not None:
            if hasattr(self.hub, 'json_log_file'):
                self.log_file = self.hub.json_log_file
            if hasattr(self.hub, 'log_file'):
                self.log_file = self.hub.log_file

        self.event_counter = 0

    ####################################################################################################################
    # main agent's loop
    ####################################################################################################################
    def agent_loop(self, max_iterations=-1, **kwargs):
        iteration = 0
        event_time = 0
        next_action = True
        while next_action is not None and (max_iterations < 0 or iteration < max_iterations):
            next_action = self.agent_decision_cycle(next_action=next_action, event_time=event_time, **kwargs)
            event_time = self.next_event_time(agent_data={}, curr_time=event_time, start_time=0, max_time=SECONDS_IN_DAY*100)
            iteration += 1

        return next_action

    ####################################################################################################################
    # This is agent's individual decision step.
    # Sub-classes must have their own meaningful implementation of agent_decision_cycle(), choose_action() and agent's
    # action methods. This is a template/abstract method.
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        """
        Called when agent is activated.
        """
        agent_data = kwargs.get('agent_data', None)
        event_time = kwargs.get('event_time', None)
        if agent_data is None or event_time is None:
            raise AssertionError("decision_data_object and event_time cannot be None")

        # choose and perform action here
        action = self.choose_action(**kwargs)
        self.perform_action(action, **kwargs)

        # log
        self.log_event({"action": action, "time": event_time})
        self.event_counter += 1

        return None

    # this is an example of an action. Descendants of DESAgent class must implement their own action methods.
    def do_nothing(self, **kwargs):
        print("DES agent empty action.")
        return None

    # this is an example of choose_action() method. Descendants of DESAgent class must implement their own choose_action().
    def choose_action(self, **kwargs):
        print("Action: do_nothing")
        return "do_nothing"

    def perform_action(self, action, **kwargs): # executes action method by name. Don't override this method.
        if hasattr(self, action) and callable(getattr(self, action)):
            function = getattr(self, action)
        else:
            underscore_action = convert_camel(action)
            if hasattr(self, underscore_action) and callable(getattr(self, underscore_action)):
                function = getattr(self, underscore_action)
            else:
                return None
        return function(action, **kwargs)


    ####################################################################################################################
    # Log event
    ####################################################################################################################
    def log_event(self, log_data, log_file=None, format='json', verbose=False):
        """
        Print log data.
        :param log_data:
        :param log_file: if string opens file, otherwise interprets it as fp
        :param format: 'json' or 'pickle'
        :param verbose:
        :return:
        """
        def _dump_data(log_data, log_file):
            if format == 'json':
                json.dump(log_data, log_file)
                log_file.write("\n")
            elif format == 'pickle':
                pickle.dump(log_data, log_file)
                log_file.write("\n")

        def _dump_to_file(log_data, log_file):
            if isinstance(log_file, str):
                with open(log_file, "a+") as fp:
                    _dump_data(log_data, fp)
            else:
                _dump_data(log_data, log_file)

        if verbose:
            print(log_data)

        if log_file is not None:
            _dump_to_file(log_data, log_file)

        if self.log_file is not None:
            _dump_to_file(log_data, self.log_file)

        if self.log_file is None and log_file is None and self.hub is not None:
            if hasattr(self.hub, 'json_log_file'):
                _dump_to_file(log_data, self.hub.json_log_file)
            if hasattr(self.hub, 'log_file'):
                _dump_to_file(log_data, self.hub.log_file)


    ####################################################################################################################
    # Needed for discrete event simulation
    ####################################################################################################################
    def next_event_time(self, **kwargs):
        """
        Return time of the first event in the given interval. Result is either between start_time and max_time or None.
        None is returned when agent does not take actions in the given time interval.
        Default behavior is to wake up once a day.
        """
        agent_data = kwargs.get('agent_data', None)
        curr_time = kwargs.get('curr_time', None)
        start_time = kwargs.get('start_time', None)
        max_time = kwargs.get('max_time', None)

        if curr_time is None or start_time is None or max_time is None:
            raise AssertionError("agent_data, curr_time, start_time and max_time cannot be None")

        next_event_time = curr_time
        while next_event_time + SECONDS_IN_DAY < start_time:
            next_event_time += SECONDS_IN_DAY

        next_event_time += SECONDS_IN_DAY

        if max_time >= float(next_event_time) >= start_time:
            return int(next_event_time)
        else:
            return None
