import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub


# This is a subclass of WorldHub that responds to 'checkMail' actions from clients with random mail.
class MailHub(WorldHub):
    mail = {}
    emailAddress = {}
    
    #def __init__(self):
        #WorldHub.__init__(self)
        #self.emailAddresses = {}
        # The mail is a dictionary with email addresses as keys and a list of unread mail as the body
        #self.mail = {}

    # API for email

    # Initialize does nothing if the email address is already in the mail dictionary
    def initialize_email(self, sender_id, recipient):
        if sender_id not in self.emailAddress:
            print("sender", sender_id, "not in email addresses: ", self.emailAddress, "not sending")
            return
        if recipient not in self.mail:
            self.mail[recipient] = []

    def get_mail(self, agent_id, data):
        if agent_id in self.emailAddress:
            address = self.emailAddress[agent_id]
            mail = self.mail[address]
            #print('mail for ' + address + ' is ' + str(mail))
            self.mail[address] = []
            return 'success', mail
        else:
            return 'fail', []

    def send_mail(self, agent_id, mail):
        # Put each message in the appropriate mailboxes. The 'to' field can be a single string or a list.
        # If the email doesn't exist yet it is created, so agents can have mail waiting when they start up.
        try:
            for message in mail:
                if 'from' not in message:
                    message['from'] = self.emailAddress[agent_id]
                if 'to' not in message:
                    print(('no \'to\' field in message, not sending:', message))
                elif isinstance(message['to'], str):
                    self.initialize_email(agent_id, message['to'])
                    self.mail[message['to']].append(message)
                elif isinstance(message['to'], list):
                    for recipient in message['to']:
                        self.initialize_email(agent_id, recipient)
                        self.mail[recipient].append(message)
            return 'success', []
        except Exception as e:
            print("problem sending mail:", e)
            print('mail is', self.mail)
            return 'fail', []

    def processRegisterRequest(self, agent_id, aux_data):
        address = aux_data[0]
        self.emailAddress[agent_id] = address
        # Someone may have already sent this agent mail before registration, so don't lose it
        if address not in self.mail:
            self.mail[address] = []
        return ['success', agent_id, []]

if __name__ == "__main__":
    MailHub().run()
