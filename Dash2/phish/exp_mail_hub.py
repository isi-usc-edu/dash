import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub


# This is a subclass of WorldHub that responds to 'checkMail' actions from clients with random mail.
class MailHub(WorldHub):
    mail = {}  # maps recipient to their mails as a dictionary mapping sender to messages.
    emailAddresses = {}
    
    #def __init__(self):
        #WorldHub.__init__(self)
        #self.emailAddresses = {}
        # The mail is a dictionary with email addresses as keys and a list of unread mail as the body
        #self.mail = {}

    # API for email

    # Initialize does nothing if the email address is already in the mail dictionary
    def initialize_email(self, id, recipient):
        sender = self.emailAddresses[id]
        if sender in self.mail and recipient not in self.mail[sender]:
            self.mail[sender][recipient] = []

    def get_mail(self, id):
        if id in self.emailAddresses:
            address = self.emailAddresses[id]
            mail = self.mail[address]
            self.mail[address] = {}
            return ['success', mail]
        else:
            return ['fail', []]

    def send_mail(self, id, mail):
        # Put each message in the appropriate mailboxes. The 'to' field can be a single string or a list.
        # If the email doesn't exist yet it is created, so agents can have mail waiting when they start up.
        try:
            sender = self.emailAddresses[id]
            for message in mail:
                if 'to' not in message:
                    print('no \'to\' field in message, ignoring:', message)
                elif isinstance(message['to'], str):
                    recipient = message['to']
                    self.initialize_email(id, recipient)
                    if sender not in self.mail[recipient]:
                        self.mail[recipient][sender] = []
                    self.mail[recipient][sender].append(message)
                    print("mail = %s" % self.mail)
                elif isinstance(message['to'], list):
                    for recipient in message['to']:
                        self.initialize_email(id, recipient)
                        if sender not in self.mail[recipient]:
                            self.mail[recipient] = []
                        self.mail[recipient][sender].append(message)
            return ['success', []]
        except Exception as exc:
            print("problem sending mail", exc, type(exc), exc.args)
            return ['fail', []]

    def processRegisterRequest(self, id, aux_data):
        self.emailAddresses[id] = aux_data[0]
        self.mail[aux_data[0]] = {}
        return ['success', id, []]

    def processSendActionRequest(self, id, action, aux_data):
        print("mail hub processing action", action, aux_data)
        if action == "getMail":
            return self.get_mail(id)
        elif action == "sendMail":
            return self.send_mail(id, aux_data)
        else:
            print("Unknown action:", action)


if __name__ == "__main__":
    MailHub().run()
