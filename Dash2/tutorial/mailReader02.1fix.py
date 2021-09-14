import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isVar
import random


class MailReader(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)

        self.readAgent("""
goalWeight doWork 1

goalRequirements doWork
    flightToBuy(flight)
    buyFlight(flight)
    sleep(1)
    forget([flightToBuy(x),buyFlight(x),sleep(x)])

goalRequirements doWork
  sendMail()
  readMail(newmail)
  processMail(newmail)
  sleep(1)
  forget([sendMail(),readMail(x),processMail(x),sleep(x),flightToBuy(x),buyFlight(x)])  # a built-in that removes matching elements from memory

transient doWork     # Agent will forget goal's achievement or failure as soon as it happens
""")
        self.primitiveActions([('readMail', self.read_mail), ('sendMail', self.send_mail), ('processMail', self.process_mail),
                               ('flightToBuy', self.flight_to_buy), ('buyFlight', self.buy_flight)])

        # Using this as a counter in the email that gets sent
        self.mailCounter = 0
        self.flights_to_buy = []     # flights that have been requested but not yet bought

    def flight_to_buy(self, goal_flight_variable_tuple):
        goal = goal_flight_variable_tuple[0]
        flight_variable = goal_flight_variable_tuple[1]

        if not isVar(flight_variable):
            return []
        result = [{flight_variable: flight} for flight in self.flights_to_buy]
        return result

    def buy_flight(self, goal_flight_tuple):
        goal = goal_flight_tuple[0]
        flight = goal_flight_tuple[1]
        print('buys flight tickets for', flight)
        self.flights_to_buy.remove(flight)
        return [{}]

    def read_mail(self, goal_mail_var_tuple):
        goal = goal_mail_var_tuple[0]
        mail_var = goal_mail_var_tuple[1]
        status, data = "", {'subject': 'buyTickets'}
        print('response to getMail is', status, data)
        print("read mail success with", data)
        return [{mail_var: data}]

    def send_mail(self, call):
        print('send mail call', call)
        data = ""
        self.mailCounter += 1
        print('send mail success with data', data)
        return [{}]

    def process_mail(self, call):
        print(call)
        mail = call[1]['subject']
        if mail == 'buyTickets':
            possible_destinations = ['New York', 'Paris', 'London', 'Shanghai']
            print(['buy tickets', random.choice(possible_destinations), 'Friday'],call)
            self.flights_to_buy.append([random.choice(possible_destinations), 'Friday'])
            return [{}]
        elif mail == 'cancelFlight':
            print('cancels flight')
            return [{}]
        else:
            return[]

    
    # def process_mail(self, call):
    #     print(call)
    #     mail = call[1]['subject']
    #     if mail == "buyTickets":
    #         print('buys plane tickets', call)
    #         self.flights_to_buy.append(['New York', 'Friday'])
    #         return [{}]
    #

if __name__ == "__main__":
    MailReader().agent_loop()
