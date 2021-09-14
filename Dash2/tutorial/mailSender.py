import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
import random


class MailSender(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)
        self.register(['flightbuyer@amail.com'])

        self.readAgent("""
goalWeight doWork 1

goalRequirements doWork
  chooseTrip(trip)
  sendTripRequest(trip)
  sleep(1)  
  forget([sendTripRequest(x), chooseTrip(x), sleep(x)])

transient doWork     # Agent will forget goal's achievement or failure as soon as it happens
                       """)
        self.mailCounter = 0
        self.colleague = 'flightagent@amail.com'
        self.favorite_destinations = ['New York', 'Paris', 'London', 'Shanghai']

    def send_trip_request(self, goal_trip_tuple):
        goal = goal_trip_tuple[0]
        trip = goal_trip_tuple[1]
        print('send mail for trip to', trip)
        status, data = self.sendAction("sendMail",
                                         [{'to': self.colleague, 'subject': 'buyTickets',
                                           'body': 'I want to go to ' + trip + str(self.mailCounter)}])
        self.mailCounter += 1
        if status == "success":
            print('send mail success with data', data)
            return [{}]
        else:
            return []

    # Bind call variable to destination
    def choose_trip(self, goal_trip_tuple):
        goal = goal_trip_tuple[0]
        trip_variable = goal_trip_tuple[1]
        return [{trip_variable: random.choice(self.favorite_destinations)}]


if __name__ == "__main__":
    MailSender().agent_loop()
