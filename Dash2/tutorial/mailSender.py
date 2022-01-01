import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
import random
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


class MailSender(DASHAgent):

    def __init__(self, args):
        DASHAgent.__init__(self)
        self.use_mailserver = args.use_mailserver
        if not self.use_mailserver:
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
        if self.use_mailserver:
            print(self.use_mailserver)
            msg = MIMEMultipart()
            msg['From'] = 'flightbuyer@mailserver.logging-test.modeling'
            msg['To'] = 'flightagent@mailserver.logging-test.modeling'
            msg['Subject'] = 'buyTickets'
            msg.attach(MIMEText('I want to go to ' + trip))
            try:
                smtp.sendmail('flightbuyer@mailserver.logging-test.modeling', 'flightagent@mailserver.logging-test.modeling', msg.as_string())
                print('send mail success: ')
                smtp.quit()
                return[{}]
            except Exception as e:
                return[{}]
        else:
            status, data = self.sendAction("sendMail",
                                             [{'to': self.colleague, 'subject': 'buyTickets',
                                               'body': 'I want to go to ' + trip + str(self.mailCounter)}])
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


def get_args():
    parser = argparse.ArgumentParser(description='Create mail sender config.')
    parser.add_argument('--use_mailserver', dest='use_mailserver', default=False, action='store_const', const=True, help='Use mail server to send emails')
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    smtp = None smtplib.SMTP('mailserver.logging-test.modeling')
    MailSender(args).agent_loop()
