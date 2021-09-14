import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isVar



class MailReader(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)
        self.register(['flightagent@amail.com'])    # Register with the running mail_hub

        self.readAgent("""
goalWeight doWork 1

goalRequirements doWork
  flightToBuy(flight)
  buyFlight(flight)
  sleep(1)
  forget([flightToBuy(x), buyFlight(x), sleep(x)])

goalRequirements doWork
  readMail(newmail)
  processMail(newmail)
  sleep(1)
  forget([readMail(x), processMail(x), sleep(x), flightToBuy(x)])  # a built-in that removes matching elements from memory

transient doWork     # Agent will forget goal's achievement or failure as soon as it happens
                       """)

        # Using this as a counter in the email that gets sent
        self.flights_to_buy = []
        self.mailCounter = 0
        
    def flight_to_buy(self, goal_flight_variable_tuple):
        goal = goal_flight_variable_tuple[0]
        flight_variable = goal_flight_variable_tuple[1]
        if isVar(flight_variable):
            return [{flight_variable: flight} for flight in self.flights_to_buy]  # all possible bindings
        elif flight_variable in self.flights_to_buy:
            return [{}]  # succeed if the flight was already bound and is a flight the agent needs to buy
        return []  # otherwise fail

    def buy_flight(self, goal_flight_tuple):
        goal = goal_flight_tuple[0]
        flight = goal_flight_tuple[1]
        print('buying flight tickets for', flight)
        self.flights_to_buy.remove(flight)
        return [{}]

    def read_mail(self, goal_mail_var_tuple):
        goal = goal_mail_var_tuple[0]
        mail_var = goal_mail_var_tuple[1]
        [status, data] = self.sendAction("getMail")
        if status == "success":
            print("successfully read mail:", data)
            return [{mail_var: data}]
        else:
            return []

    # This agent processes email by generating an internal list of flights to be bought and/or canceling flights
    def process_mail(self, goal_mail_list_tuple):
        goal = goal_mail_list_tuple[0]
        mail_list = goal_mail_list_tuple[1]

        print('processing', mail_list)
        for mail in mail_list:
            if mail['subject'] == 'buyTickets':
                # Body should be 'I want to go to ' + destination (which currently includes an email serial number)
                ix = mail['body'].find('I want to go to')
                if ix == -1:
                    return []    # Can't read the destination: fail
                destination = mail['body'][ix + 16:]
                print('  buy tickets', destination, 'Friday', mail)
                self.flights_to_buy.append([destination, 'Friday'])
            elif mail['subject'] == 'cancelFlight':
                print('  cancels flight')
            else:
                print('  unknown request:', mail['subject'])
        return [{}]


if __name__ == "__main__":
    MailReader().agent_loop()
