import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub, ServeClientThread


# This is a subclass of WorldHub that responds to 'checkMail' actions from clients with random mail.
class MailHub(WorldHub):
    def __init__(self):
        WorldHub.__init__(self)
        # The mail is a dictionary with email addresses as keys and a list of unread mail as the body
        self.mail = {}

    def createServeClientThread(self, args_tuple):
        (client, address) = args_tuple
        return MailServeClientThread((client, address), self)

    # API for email

    # Initialize does nothing if the email address is already in the mail dictionary
    def initialize_email(self, address):
        if address not in self.mail:
            self.mail[address] = []

    def get_mail(self, address):
        if address not in self.mail:
            return -1
        mail = self.mail[address]
        self.mail[address] = []
        return mail

    def send_mail(self, mail):
        # Put each message in the appropriate mailboxes. The 'to' field can be a single string or a list.
        # If the email doesn't exist yet it is created, so agents can have mail waiting when they start up.
        try:
            for message in mail:
                if 'to' not in message:
                    print('no \'to\' field in message, ignoring:', message)
                elif isinstance(message['to'], str):
                    self.initialize_email(message['to'])
                    self.mail[message['to']].append(message)
                elif isinstance(message['to'], list):
                    for recipient in message['to']:
                        self.initialize_email(recipient)
                        self.mail[recipient].append(message)
        except:
            print("problem sending mail")


# This subclass of serveClientThread handles the work of a persistent client/server pairing
# and can maintain state for the client agent. Shared world state should then be handled with
# static variables I guess.
class MailServeClientThread(ServeClientThread):
    def __init__(self, args_tuple1, mail_hub):
        (client, address) = args_tuple1
        ServeClientThread.__init__(self, (client, address))
        self.mailHub = mail_hub
        self.emailAddress = None

    def processRegisterRequest(self, agent_id, aux_data):
        self.emailAddress = aux_data[0]
        return ['success', agent_id, []]

    def processSendActionRequest(self, id, action, aux_data):
        print("mail hub processing action", action, aux_data)
        if action == "getMail":
            return self.get_mail()
        elif action == "sendMail":
            return self.send_mail(aux_data)
        else:
            print("Unknown action:", action)

    def get_mail(self):
        mail = self.mailHub.get_mail(self.emailAddress)
        return ['success', mail]

    def send_mail(self, mail):
        self.mailHub.send_mail(mail)
        return ['success', []]


if __name__ == "__main__":
    MailHub().run()
