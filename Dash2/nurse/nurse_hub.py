import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub
import random
import numbers


class Event:
    def __init__(self, agent, event_type, computer, patient=None, medication=None, spreadsheet_loaded=None):
        self.type = event_type  # login, logout, walk away, load spreadsheet, read spreadsheet, write to spreadsheet
        self.agent = agent
        self.computer = computer
        self.patient = patient
        self.medication = medication
        self.spreadsheet_loaded = spreadsheet_loaded

    def __str__(self):
        return "N" + str(self.agent) + " " + self.type + \
               ((" " + self.medication + " to " + self.patient) if self.type == "write" else "") +\
               " on C" + str(self.computer) +\
               ("" if self.spreadsheet_loaded is None else (" in S:" + self.spreadsheet_loaded))


class NurseHub(WorldHub):

    def __init__(self, number_of_computers=10, number_of_possible_medications=10, autologout=2, port=None):
        WorldHub.__init__(self, port=port)
        self.init_world(None, (number_of_computers, number_of_possible_medications, autologout))

    # agent_id is a bogus argument so an agent can call this as an action on the hub and we can also
    # call it on the hub. Will fix.
    def init_world(self, agent_id, args_tuple):
        # Initialize the computers to all be available.
        (number_of_computers, number_of_possible_medications, autologout) = args_tuple
        self.number_of_computers = number_of_computers
        cr = list(range(0, self.number_of_computers))
        self.logged_on = [None for i in cr]
        self.logged_out = [None for i in cr]
        self.present = [None for i in cr]  # agent who is present at the computer.
        self.unattended_count = [0 for i in cr]
        self.spreadsheet_loaded = [None for i in cr]
        self.events = []  # list of events
        # self.possible_medications = ['_percocet', '_codeine', '_insulin', '_zithromycin']
        self.possible_medications = ['_m' + str(i) for i in range(1, number_of_possible_medications + 1)]
        self.medication_for_patient = dict()
        self.time_out = autologout  # If > 0, any account left unattended for this long will be logged out
        self.time_step = 0

    def find_open_computers(self, agent_id, data):
        return 'success', [i for i in range(1, self.number_of_computers+1) if self.logged_on[i-1] is None]

    def find_all_computers(self, agent_id, data):
        return 'success', list(range(1, self.number_of_computers + 1))

    def login(self, agent_id, data):
        print("Logging in", agent_id, "with", data)
        computer = data[0]-1
        self.logged_on[computer] = agent_id           # agent indexes the computer from 1..n, the list is indexed from 0..n-1
        self.present[computer] = agent_id
        return 'success'

    # Making these atomic actions inside the hub to reduce the number of times that several agents see the same
    # 'available' computer and log into it in the next step.
    # I haven't put a thread lock on this so it still might happen.

    # This one finds a computer with no-one logged in
    def login_to_open_computer(self, agent_id, data):
        open_computers = [i for i in range(1, self.number_of_computers+1) if self.logged_on[i-1] is None]
        return self.login_to_computer_from_list(agent_id, data, 'open', open_computers)

    # This one finds a computer with no-one present, although someone might be logged in
    def login_to_unattended_computer(self, agent_id, data):
        unattended_computers = [i for i in range(1, self.number_of_computers+1) if self.present[i-1] is None]
        return self.login_to_computer_from_list(agent_id, data, 'unattended', unattended_computers)

    def login_to_computer_from_list(self, agent_id, data, tag, list_of_computers):
        print('login req from', agent_id, 'with', tag, list_of_computers)
        if list_of_computers:  # Might be empty list as computed in one of the calling methods
            target_computer = random.choice(list_of_computers)
            self.logged_on[target_computer-1] = agent_id
            self.present[target_computer-1] = agent_id
            self.events.append(Event(agent_id, "login", target_computer))
            return target_computer
        self.events.append(Event(agent_id, "login", 'fail'))
        return 'fail'

    def logout(self, agent_id, data):
        print("Logging out", agent_id, 'with', data)
        if isinstance(data[0], numbers.Number):
            computer = data[0]-1
            self.logged_on[computer] = None
            self.logged_out[computer] = agent_id
            self.events.append(Event(agent_id, "logout", computer+1))
            return 'success'
        else:
            return 'fail'

    # Might still be logged in, but when not present could be logged out or overwritten by another
    def walk_away(self, agent_id, data):
        print('walking away from the computer:', agent_id, data)
        if not isinstance(data, numbers.Number):
            return 'fail'
        if self.present[data-1] == agent_id:
            self.present[data-1] = None
            self.events.append(Event(agent_id, "walk_away", data))
            return 'success'
        else:
            return 'fail'

    def load_spreadsheet(self, agent_id, args_tuple1):
        # Check no other agent is present at the computer (don't log the user in automatically if there is no-one logged in)
        (patient, computer) = args_tuple1
        if self.present[computer-1] == agent_id or self.present[computer-1] is None:
            if self.logged_on[computer-1] is not None:  # Anyone could be logged in
                self.spreadsheet_loaded[computer-1] = patient
                return 'success'
            else:  # no-one is logged in
                return 'open'
        else:  # another agent is physically present at the computer
            return 'blocked', self.present[computer-1]

    def read_spreadsheet(self, agent_id, args_tuple2):
        # Read the correct medication for the patient whose spreadsheet is loaded on the computer.
        # Check the agent is at the computer (also makes the agent be present if no other agent already is).
        (patient, computer) = args_tuple2
        if self.present[computer-1] is None:
            return 'open', None, None
        elif self.present[computer-1] != agent_id:
            return 'computer_blocked by ' + str(self.present[computer-1]), None, None  # someone else is logged on
        # If there isn't yet a medication for this patient, pick one at random. If no patient
        # is loaded on the computer, fail.
        real_patient = self.spreadsheet_loaded[computer-1]
        if real_patient is None:
            return 'no_patient_loaded', None, None
        if real_patient not in self.medication_for_patient:
            self.medication_for_patient[real_patient] = random.choice(self.possible_medications)
        self.events.append(Event(agent_id, "read", computer, patient=patient, spreadsheet_loaded=real_patient))
        return 'success', self.medication_for_patient[real_patient], real_patient

    def write_spreadsheet(self, agent_id, args_tuple3):
        (patient, computer, medication) = args_tuple3
        if self.present[computer-1] == agent_id or self.present[computer-1] is None:  # no other agent at the computer
            if self.logged_on[computer-1] is not None:  # someone is logged on
                print("Writing event", agent_id, "using", computer, "for", patient, medication,
                      "(loaded ", self.spreadsheet_loaded[computer-1], ")")
                self.events.append(Event(agent_id, "write", computer, patient=patient, medication=medication,
                                         spreadsheet_loaded=self.spreadsheet_loaded[computer-1]))
                return 'success', self.spreadsheet_loaded[computer-1]
            else:  # no-one logged on
                return 'open', None
        else:
            return 'computer_blocked', self.spreadsheet_loaded[computer-1]

    # This is no longer used, because the process of logging in if no-one is logged in is a conscious agent action
    def check_present(self, agent_id, computer):
        if self.present[computer-1] is None:
            self.present[computer-1] = agent_id
        return self.present[computer-1] == agent_id

    def print_events(self):
        print(len(self.events), 'events:')
        for event in self.events:
            print(event)
        print(len([e for e in self.events if e.patient != e.spreadsheet_loaded]),
              "entries on the wrong spreadsheet out of", len(self.events))
        print('time step =', self.time_step)

    # These are not methods an agent should use, but the experimental harness can call them to examine
    # the data after a run and declare a timestep for book-keeping.
    def show_events(self, agent_id, data):
        return 'success', self.events

    def tick(self, agent_id, data):
        self.time_step += 1
        # Increment the unattended count for each unattended computer
        for c in range(0, self.number_of_computers):
            if self.present[c] is None and not self.logged_on[c] is None:
                self.unattended_count[c] += 1
                if self.time_out > 0 and self.unattended_count[c] >= self.time_out:
                    agent = self.logged_on[c]
                    self.logged_out[c] = agent
                    self.logged_on[c] = None
                    self.events.append(Event(agent, "autologout", c))
                    print("AutoLogged", agent, "out of", (c+1), "after", self.time_out)
                    self.unattended_count[c] = 0
            else:
                self.unattended_count[c] = 0
        print('tick', self.time_step, self.unattended_count)


if __name__ == "__main__":
    # Take port as a command-line argument
    if len(sys.argv) > 1:
        nh = NurseHub(port=int(sys.argv[1]))
    else:
        nh = NurseHub()
    nh.trace_handler = False  # don't print out all the message lengths and types
    nh.run()
    # When the hub is stopped with 'q', print out the results
    nh.print_events()

