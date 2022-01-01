import sys; sys.path.extend(['../../'])
import random
import operator
import sys
from six import iteritems
from Dash2.core.dash_agent import DASHAgent


class SimilarityAgent(DASHAgent):

    username_list = {'a':1, 'b':2, 'c':3}
    password_list = {'pass1':1, 'pass2':2, 'pass3':3}
    cogThreshold = 62

    # add socket
    def __init__(self):
        DASHAgent.__init__(self)

        response = self.register()
        if response[0] != "success":
            print("Error: world hub not reachable - exiting ")
            sys.exit()
        self.id = response[1]

        # distribution of probabilities for every service type
        self.serviceProbs = {'mail': 0.35, 'social_net':0.85, 'bank':1.0}
        # bias between memorizing or writing down
        self.simPassword = {'same': 0.3, 'similar': 0.8, 'unique': 1.0}

        # initial cong. burden
        self.cognitiveBurden = 0
        # usernames used - dict {username:complexity}
        self.knownUsernames = {}
        # passwords used - dict {password:complexity}
        self.knownPasswords = {}

        # i'm not really clear about usage of primitive actions vs just defining
        # new goals
        self.primitiveActions([
        ('setupAccount', self.setupAccount),
        ('signIn', self.signIn),
        ('signOut', self.signOut),
        ])

        self.readAgent( """

goalWeight doWork 1         # repeat the proces

goalRequirements doWork
    setupAccount(service_type)
    signIn(service)
    signOut(service)

""")
        # self.register("test")


    def setupAccount(self, service_type=None, service=None, requirements=None):
        ''' Should be equivalent to createAccount subgoal in prolog version
        It takes service type as an input, and based on that decides which
        username to use[1]. Then, it picks the password and submits the info.

        Based on the service response it adjusts username and password.
        Finally, if successful, it stores info in memory (in one of couple of ways)

        Flow:
            initializeContact(service_type)
            choose username
            choose password - for now random
                memorizeUserName
                memorizePassword
                writeDownUsername
                writeDownPassword
            submit info
                if not ok, repeat

        Defined Actions:
            1. getAccount
            2. createAccount (in utils.py)


        [1] we might add the fact that banks usually don't really let you pick
        password, which additionally adds to the cognitive burden.
        '''

        
        if service_type is None:
            # choose the service type, and find the actuall service
            service_type = distPicker(self.serviceProbs, random.random())
            # Decide the service to log into
            response = self.sendAction('getAccount', [service_type])
            service = response[1]   # This should be second entry of the response

        ### choose Username
        if bool(self.knownUsernames):
            username = random.choice(self.knownUsernames)
        else:
            username = random.choice(list(self.username_list.keys()))

        ### choose Password
        desired_pass = random.choice(list(self.password_list.keys()))
        # if there are requirements verify that the password complies them
        if requirements is not None:
            while not requirements.verify(username, desired_pass):
                desired_pass = random.choice(list(self.password_list.keys()))


        if (self.password_list[desired_pass] + self.cognitiveBurden) < self.cogThreshold:
            password = desired_pass
            # add to the list of known pass, and remove from potential passes
            self.knownPasswords[desired_pass] = self.password_list[desired_pass]
            del self.password_list[desired_pass]
        elif distPicker(self.memoBias, random.random()) == 'same':
            password = max(iteritems(stats), key=operator.itemgetter(1))[0]
        else:
            password = desired_pass + "00"
            self.knownPasswords.append(password)


        result = self.sendAction('createAccount', [service, username, password])
        if result[0] == 'success':
            print('Success: Account Created')
            print('Password: ' + password)
        elif result[0] == 'failed:user':
            print('Failed: username already exists (should not happen yet)')
        elif result[0] == 'failed:reqs':
            self.setupAccount(service_type, service, result[1])

        return 'success'


if __name__ == "__main__":
    agent1 = SimilarityAgent()
    agent2 = SimilarityAgent()
    agent1.agent_loop()
    agent2.agent_loop()
