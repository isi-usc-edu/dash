import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.parameter import Parameter, IntegerUniform
from Dash2.core.system2 import isVar


class Nurse(DASHAgent):

    parameters = [Parameter('n_steps_to_patient', distribution=IntegerUniform(1, 3))]  # unlike randrange, includes 3

    def __init__(self, ident=0, patients=['_joe', '_harry', '_david', '_bob'], prob_check_spreadsheet=0):
        DASHAgent.__init__(self)

        # Testing
        print('agent', ident, 'number of steps is', self.n_steps_to_patient)

        self.readAgent("""

goalWeight doWork 1

goalRequirements doWork
    pickPatient(patient)
    findMedications(patient, medications, computer)
    walkAway(computer)
    findStepsNeeded(patient, nsteps)
    deliverMedications(patient, medications, nsteps)
    forgetNT([alreadyLoggedOn(c, s), findComputer(c, s)])
    logDelivery(patient, medications)
    forget([pickPatient(x), findMedications(x, y), deliverMedications(x, y), logDelivery(x, y), alreadyLoggedOn(c, s), logIn(c, s), logOut(c), findComputer(c, s), readSpreadsheet(p, c, m), loadSpreadsheet(p), writeSpreadsheet(p, c, m), walkAway(c), oneLess(x,y)])

goalRequirements doWork
    canWait()
    wait()
    forget([canWait(), wait(), findMedications(x,y), findComputer(c,s), logIn(c,s), deliverMedications(x,y), alreadyLoggedOn(c, s), readSpreadsheet(p,c,m), oneLess(x,y)])

goalRequirements findMedications(patient, medications, computer)
    findComputer(computer, session)
    loadSpreadsheet(patient, computer, session)
    readSpreadsheet(patient, computer, medications)

goalRequirements deliverMedications(patient, medication, stepsLeft)
    oneLess(stepsLeft, newSteps)
    deliverMedications(patient, medication, newSteps)

goalRequirements deliverMedications(patient, medication, 0)
    administerMedications(patient, medication)

goalRequirements logDelivery(patient, medications)
    findComputer(computer, session2)
    loadSpreadsheet2(patient, computer, session2)
    writeSpreadsheet(patient, computer, medications)
    logOut(computer)
    walkAway(computer)

goalRequirements findComputer(computer, session)
    alreadyLoggedOn(computer, session)

goalRequirements findComputer(computer, session)
    logIn(computer, session)

transient doWork

    """)

        self.primitiveActions([('pickPatient', self.pick_patient), #('deliverMedications', self.deliver_medications),
                               ('loadSpreadsheet', self.load_spreadsheet), ('loadSpreadsheet2', self.load_spreadsheet),
                               ('readSpreadsheet', self.read_spreadsheet), ('writeSpreadsheet', self.write_spreadsheet),
                               ('alreadyLoggedOn', self.already_logged_on), ('logIn', self.log_in),
                               ('logOut', self.log_out), ('wait', self.wait), ('canWait', self.can_wait),
                               ('walkAway', self.walk_away), ('forgetNT', self.forget)])
        # self.traceAction = True  # uncomment to see more about the internal actions chosen by the agent
        #self.traceGoals = True
        #self.traceUpdate = True
        #self.traceForget = True
        self.id = ident
        self.register()

        self.patient_list = patients
        self.current_patient = None
        self.computer = None    # computer the agent believes it's logged into
        self.at_computer = False
        self.history = []  # history of the agent's actions

        self.blocked = False  # The agent can't always wait and try again, but can when it is blocked on the computer it's trying to use
        self.times_waiting = 0  # There's also a timeout
        self.max_times_waiting = 5

        # Hack
        self.tried_once = False

    def __str__(self):
        return "<Nurse " + str(self.id) + ">"

    def pick_patient(self, args_tuple):
        (goal, patient_variable) = args_tuple
        if self.patient_list:
            self.current_patient = self.patient_list.pop()
            print('starting to work on', self.current_patient)
            return [{patient_variable: self.current_patient}]
        else:
            return []

    def administer_medications(self, args_tuple1):
        # Must walk away from the computer
        (goal, patient, medication) = args_tuple1
        self.sendAction("walkAway", self.computer)
        print(self.id, 'delivers', medication, 'to patient', patient)
        return [{}]

    def load_spreadsheet(self, args_tuple2):
        #print "Session on", computer, "is considered", session, "in", (predicate, patient, computer, session)
        (predicate, patient, computer, session) = args_tuple2
        result = self.sendAction("loadSpreadsheet", [patient, computer])
        if result == 'success':
            self.at_computer = True
            return [{}]
        else:  # agent is not logged into the computer so can't load a spreadsheet but could log in maybe
            self.at_computer = False
            self.computer = None
            print('result from load_spreadsheet is', result, ', forgetting logged on')
            self.forget(('forget', [('alreadyLoggedOn', computer, 's'), ('logIn', computer, 's'), ('findComputer', computer, 's')]))
            if not self.tried_once:
                self.tried_once = True
                #self.traceGoals = True
                #self.traceUpdate = True
                return 'TryAgain'  # Should result in re-trying the login
            else:
                return []

    def read_spreadsheet(self, args_tuple3):
        (predicate, patient, computer, medications_variable) = args_tuple3
        self.at_computer = True
        [status, medication, real_patient] = self.sendAction("readSpreadsheet", [patient, computer])   # returns the medication for the patient
        print(self.id, status, 'reading medication', medication, 'for', patient, 'on', computer, '(', real_patient, 'actually loaded)')
        if status == 'success':
            return [{medications_variable: medication}]
        else:
            if status == 'computer_blocked':
                self.blocked = True
            return []

    def write_spreadsheet(self, args_tuple4):
        (predicate, patient, computer, medication) = args_tuple4
        self.at_computer = True
        (status, written_patient) = self.sendAction("writeSpreadsheet", [patient, computer, medication])
        if status == 'success':
            print(self.id, 'opening spreadsheet and writing patient info:', medication, patient, 'on', computer)
            return [{}]
        elif status == 'computer_blocked':
            print(self.id, 'BLOCKED opening spreadsheet and writing patient info:', medication, patient, 'on', computer)
            self.blocked = True  # can wait for the computer to write too.
        else:
            print('status', status, written_patient, 'while', self.id, 'opening spreadsheet and writing patient info:', medication, patient, 'on', computer)
            return []

    def log_out(self, args_tuple5):
        (logout, computer) = args_tuple5
        print(self.id, 'logs out of computer', computer)
        self.sendAction('logout', [computer])
        self.computer = None
        return[{}]     # call[1] was a constant, there is nothing to bind here

    def already_logged_on(self, args_tuple6):
        (goal, computer_var, session_var) = args_tuple6
        if self.computer is None:
            #print 'not already logged on to a computer'
            return []
        else:
            print(self.id, 'believes already logged onto', self.computer)
            # If you believe you're logged on, you also believe your patient's spreadsheet is loaded (this is key)
            self.known('loadSpreadsheet2', [self.current_patient, self.computer, session_var])
            return [{computer_var: self.computer, session_var: "_old"}]  # mark as an old session if already logged in

    # Explicitly walk away at the end of each task so others can use the computer (is implicit in delivering medication,
    # and might be removed from the end as part of testing).
    def walk_away(self, args_tuple7):
        (walk_predicate, computer) = args_tuple7
        print(self.id, 'walks away from', computer)
        self.at_computer = False
        self.sendAction("walkAway", computer)
        return [{}]

    # Changed this to make finding an open computer and logging into it an atomic action, since when there are
    # many agents they may all see the same open computers and then overrun each other at the beginning, which is
    # not the scenario we're looking for.
    def log_in(self, args_tuple8):
        (login, computer_variable, session_var) = args_tuple8
        open_computer = True
        self.computer = self.sendAction("LoginToOpenComputer")
        if self.computer == 'fail':  # No open computers. Pick one at random which will log someone else off
            open_computer = False
            self.computer = self.sendAction("LoginToUnattendedComputer")
            if self.computer == 'fail':  # can't find any unattended computers on the hub!
                self.computer = None
                self.blocked = True  # Allow the agent to wait a turn
                print(self.id, 'cannot find an unattended computer')
                return []
        print(self.id, 'login to', 'open' if open_computer else 'unattended', 'computer:', self.computer)
        self.at_computer = True
        return[{computer_variable: self.computer, session_var: "_new"}]  # mark as a new session if we just logged in

    # If the main task fails because of contention on the computers, wait a turn to see if it improves
    def can_wait(self, goal):
        return [{}] if self.blocked and self.times_waiting < self.max_times_waiting else []

    def wait(self, goal):
        print(self.id, 'waiting')
        self.blocked = False  # will have to be re-established
        self.times_waiting += 1
        return [{}]

    # Bind the new_val_var to one less than the old one, but fail if the answer is negative.
    def one_less(self, args_tuple9):
        (predicate, old_val, new_val_var) = args_tuple9
        if isVar(new_val_var):
            if isVar(old_val):
                return []  # that won't work
            elif old_val > 0:
                print(self.id, old_val - 1, 'steps remaining')
                # When not running within the experiment simulation we need to move the hub on a tick.
                # This would not require special coding with the event queue but that's untested.
                # Comment this line out for the experiment!
                self.sendAction("tick", [])
                return [{new_val_var: old_val - 1}]
            else:
                return []
        elif isVar(old_val):
            return [{old_val: new_val_var + 1}]
        elif old_val == new_val_var + 1:
            return [{}]
        else:
            return []

    # Bind the steps to the parameter
    def find_steps_needed(self, args_tuple10):
        (goal, patient, steps) = args_tuple10
        return [{steps: self.n_steps_to_patient}]


# maybe add some sort of variable to account for human error, even if logged in successfully 

if __name__ == '__main__':
    # Take the port as an argument
    if len(sys.argv) > 1:
        Nurse(port=int(sys.argv[1])).agent_loop()
    else:
        Nurse().agent_loop()
