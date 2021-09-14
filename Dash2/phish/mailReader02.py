import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent


class MailReader(DASHAgent):

    def __init__(self):
        DASHAgent.__init__(self)

        self.readAgent("""
goalWeight doWork 1

goalRequirements doWork
  flightToBuy(flight)   # binds 'flight' to a flight to be bought if there is one, otherwise fails.
  buyFlight(flight)
  sleep(1)
  forget([flightToBuy(x),buyFlight(x)])

goalRequirements doWork
  sendMail()
  readMail(newmail)
  processMail(newmail)
  sleep(1)
  forget([sendMail(),readMail(x),sleep(x)])  # a built-in that removes matching elements from memory

transient doWork     # Agent will forget goal's achievement or failure as soon as it happens
""")
        self.primitiveActions([('readMail', self.read_mail), ('sendMail', self.send_mail), ('processMail', self.process_mail)])

        # Using this as a counter in the email that gets sent
        self.mailCounter = 0
        self.flights_to_buy = []

    def read_mail(self, call):
        mail_var = call[1]
        #[status, data] = self.sendAction("getMail")
        [status, data] = ["", {'subject': 'buyTickets'}]
        print('response to getMail is', status, data)
        print("read mail success with", data)
        return [{mail_var: data}]

    def send_mail(self, call):
        print('send mail call', call)
        #[status, data] = self.sendAction("sendMail",
        #                                 [{'to': 'mailagent@amail.com', 'subject': 'test',
        #                                   'body': 'this is test message ' + str(self.mailCounter)}])
        data = ""
        self.mailCounter += 1
        print('send mail success with data', data)
        return [{}]

    def process_mail(self, call):
        print(call)
        mail = call[1]['subject']
        if mail == "buyTickets":
            print('buys plane tickets', call)
            # Store the flight in flights_to_buy
            self.flights_to_buy.append(1)
            return [{}]
        elif mail == 'cancelFlight':
            print('cancels flight')
            return [{}]
        else:
            return[]


if __name__ == "__main__":
    MailReader().agent_loop()
