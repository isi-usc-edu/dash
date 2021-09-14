# todo & notes
# Changing to use spreading activation in system 1 to model password forgetting and mistaking passwords between sites.
# add counters for memorizations, resets, etc...
# check termination

### Create acc
##### - add username list as dict username:complexity
##### in the code refered to as username_list; UN does not contribute to CB yet
##### - add password list as dict pass:complexity
##### in the code referred to as pass list
##### - add update beliefs in the end^

### signIn
##### - add reset password branch

### Utils
##### find a way of rasing an error (42)
##### finish elaborate pass choosing

"""
Notes: 3/13/17 - got to the point where I'm recording the number of passwords created and manipulating the constraint
difficulty on the hub, and computing reuse opportunities. It looks like this will work, need to compute expected
number of compromised sites based on (1) base prob of direct attack,
(2) prob of password attack that is higher for shorted passwords and
(3) possible reuse attacks (will assume a high probability they are executed).
Probably the uncanniness will depend on those numbers, which points to the value of FARM
"""


import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.parameter import Parameter
from Dash2.core.system2 import isVar
from Dash2.core.measure import Measure
from Dash2.pass_attacker.utils import distPicker
from Dash2.pass_attacker.minimum_spanning_tree import minimum_spanning_tree
import math
import random

class PasswordAgent(DASHAgent):

    parameters = [Parameter('initial_belief', default=0.65, range=(0, 1)),  # initial strength of beliefs
                  Parameter('cognitive_threshold', default=30),
                  # this forget rate chosen to give ~15% resets with only 9 sites. Should be tuned for more sites.
                  Parameter('initial_password_forget_rate', default=0.215),  # 0.0025 from bruno_user.pl
                  Parameter('strengthen_factor', default=4),  # Factor in strengthening the pwd each successful use (strengthenScalar in bruno_user.pl)
                  Parameter('forget_rate_discount', default=2.364),  # factor by which the forget rate decreases each successful use, from bruno_user.pl
                  # how passwords are chosen either from the list of new or existing passwords
                  Parameter('choose_password_method', value_set=['random', 'list-order'], default='random'),
                  ]

    # Note: this is really a measure of a set of agents, derived from
    measures = [Measure('proportion_of_resets', target=0.15, backing='Florencio & Herley 07')]

    def __init__(self):
        DASHAgent.__init__(self)

        response = self.register()
        if response is None or response[0] != "success":
            print("No world hub was found. This agent requires a password simulation hub, e.g. pass_sim_hub.py")
            return  # used to sys.exit() here but that makes it impossible to manage the process by e.g. starting a hub
        self.id = response[1]

        # Added by Jim based on bruno_user.pl. This is the list of all possible password choices for
        # the agent, not the ones the agent currently users.
        self.password_list = ['p', 'P', 'pw', 'Pw', 'pw1', 'Pw1', 'pass', 'Pass', 'pas1', 'Pas1', 'pass1', 'Pass1',
                              'PaSs1', 'password', 'P4ssW1', 'PassWord', 'PaSs12', 'PaSsWord', 'PaSsW0rd', 'P@SsW0rd',
                              'PassWord1', 'PaSsWord1', 'P4ssW0rd!', 'P4SsW0rd!', 'PaSsWord12', 'P@SsWord12',
                              'P@SsWoRd12', 'PaSsWord!2', 'P@SsWord!234', 'P@SsWord!234', 'MyP4SsW0rd!',
                              'MyP4SsW0rd!234', 'MyP@SsW0rd!234', 'MyPaSsWoRd!234?', 'MyPaSsW0Rd!234?',
                              'MyS3cUReP@SsW0rd!2345', 'MyV3ryL0ngS3cUReP@SsW0rd!2345?']

        # distribution of probabilities for every service type. These are cumulative probabilities, so order matters.
        self.service_type_probs = [('mail', 0.35), ('social_net', 0.85), ('bank', 1.0)]
        # bias between memorizing or writing down
        self.memoBias = [('reuse', 0.5), ('write_down', 1.0)]
        # initial strength of beliefs
        #self.initial_belief = 0.65  # now a parameter
        # forgetting rate - percent of belief lost
        self.password_forget_rate = {}
        # strengthening rate
        self.strengtheningRate = 0.2  # not currently used


        self.cognitiveBurden = 0  # Perhaps this is computed at each point, haven't figured out the details yet.
        # These were copied from bruno_user.pl in lib/logic - check for comments there.
        #self.cognitiveThreshold = 30  # was 68 in the prolog but trying one that limits to something like 12 passwords
        # (the prolog version included the cost for usernames, not currently included)
        self.recallThreshold = 0.5  # from bruno_user.pl, not currently used
        self.passwordReusePriority = 'long' # not currently used
        self.passwordReuseThreshold = 54  # not currently used
        self.passwordForgetRateStoppingCriterion = 0.0005  # from bruno_user.pl, not currently used
        # pairs used - dict {service:[username, password]}
        self.known = {}
        # usernames used - dict {username:complexity} (I changed to just a list - Jim)
        self.knownUsernames = []
        # passwords used - dict {password:complexity} (I changed to just a list - Jim)
        self.known_passwords = []
        # list of writen pairs
        self.writtenPasswords = []
        # USER beliefs. self.beliefs[belief] is a triple [username, password, belief] where 0 <= belief <= 1
        self.beliefs = {}

        self.username_list = ["joe@gmail.com"]  # ['user1', 'user12', 'admin']  # user names are currently randomly chosen from these

        # I need some clarification on this. In the prolog version, this is only incremented when the password fails
        # I'm doing the same for now and renaming as 'failed_logins'.
        self.failed_logins = 3  # from bruno_user.pl

        self.num_login_attempts = 0
        self.num_logins = 0
        self.num_reset_attempts = 0
        self.num_resets = 0

        # The agent goal description is short, because the rational task is not that important here.
        self.readAgent("""

goalWeight doWork 1         # repeat the proces

goalRequirements doWork
    checkTermination(criterion, beliefs)
    forget([checkTermination(c, b)])

goalRequirements doWork
    setupAccount(service_type, service)
    signIn(service)
    signOut(service)
    forget([setupAccount(st,s), signIn(s), signOut(s), resetPassword(s)])

#resetPassword(service)  # skip this step

# This means that every iteration it will need to be re-achieved
transient doWork

""")
        self.trace_action = True

        # Same passwords reinforce across services. Different passwords inhibit each other on one service.
        self.create_neighbor_rule('password', self.link_password_nodes)



    # service_type_var may be unbound or bound to a requested service_type. service_var is unbound
    # and will be bound to the result of setting up the service
    def setup_account(self, args_tuple):
        ''' Should be equivalent to createAccount subgoal in prolog version
        It takes service type as an input, and decides which
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
        (goal, service_type_var, service_var) = args_tuple
        if isVar(service_type_var):
            # choose the service type, and find the actual service
            service_type = distPicker(self.service_type_probs, random.random())

        # Decide the service to log into
        [status, service, requirements] = self.sendAction('getAccount', [service_type])
        print('chosen account', 'already' if service in self.beliefs else 'to', \
            'set up', service_type, status, service, requirements)

        ### choose Username
        # if the list of existing usernames is not empty, pick one at random,
        # else pick one from list of predefined usernames
        # here we should add some logic for cognitive burden but I didn't play with
        # it as we didn't have usernames elaborately in prolog
        if self.knownUsernames:
            username = random.choice(self.knownUsernames)
        else:
            username = random.choice(self.username_list)

        password = self.choose_password(username, requirements)

        # Make sure a node exists for this password for every known service
        # The same password is linked positively across services,
        # and different passwords are linked negatively at each service (this is enforced by neighbor rules)
        for s2 in self.beliefs:
            self.fact_to_node(('password', s2, password))

        # If account is be created, update beliefs else repeat
        # I am not sure if it would make more sense to keep beliefs local in this
        # case
        if service in self.beliefs:
            status = 'failed:user'  # only make one account per service, fake failing if we already made one
        else:
            [status, data] = self.sendAction('createAccount', [service, username, password])
        #print 'create account result:', [status, data]
        if status == 'success':
            print('Account created on', service, 'with user', username, 'and password', password, requirements)
            if password not in self.writtenPasswords:
                self.beliefs[service] = [username, password, self.initial_belief]
            else:
                self.beliefs[service] = [username, password, self.initial_belief, 0.9999]
            self.password_forget_rate[service] = self.initial_password_forget_rate  # following bruno_user.pl but not a direct copy
            if isVar(service_type_var):
                return [{service_type_var: service_type, service_var: service}]
            else:
                return [{service_var: service}]
        elif status == 'failed:user':
            #print 'Failed to create account on', service, ': username already exists'  # too frequent to print
            # Should succeed in 'setting up' the account though
            if isVar(service_type_var):
                return [{service_type_var: service_type, service_var: service}]
            else:
                return [{service_var: service}]
        elif status == 'failed:reqs':
            #self.setupAccount(service_type, service, result[1])
            print('Failed to create account on ', service, ': password failed the requirements')
            return []
        else:
            print('unknown result for creating account:', service, status, data)
            return []

    def sign_in(self, args_tuple1):
        ''' This should be equivalent to signIn subgoal in prolog version
        User looks for service beliefs on the worldHub, and based on the strength
        of his belief tries either one of the known passwords or the password for
        which agent has beliefs. If he has no account on that service it proceeds
        to create the account.
        Depending on the success of the action, it updates strength beliefs.

        Defined Actions:
            1. getServType
            2. retrieveInformation
            3. signIn

        '''
        (goal, service) = args_tuple1
        self.num_login_attempts += 1
        # check if user has account
        if service not in self.beliefs or not self.beliefs[service]:
            print("User has no beliefs for this account:", service, self.beliefs)

        [username, password, belief] = self.beliefs[service]
        # Select password: essentially the weaker the belief is the greater the chance
        # that user will just pick one of their known username/passwords
        distribution = [(password, belief), ('other_known', (1 + belief) * 0.5), ('reset', 1.0)]
        changed_password = False
        decision = distPicker(distribution, random.random())
        if decision == 'other_known':
            if self.knownUsernames and self.known_passwords:
                changed_password = True
                old_username, old_password = username, password
                username = random.choice(self.knownUsernames)
                password = random.choice(self.known_passwords)
                print('changed password belief to', password, ', beliefs', distribution)
            else:
                print('would have changed but usernames=', self.knownUsernames, 'and pw=', self.known_passwords)
        elif decision == 'reset':
            print('resetting the password for', service)
            self.reset_password(('predicate', service))  # This updates the beliefs appropriately
            [username, password, belief] = self.beliefs[service]

        # Try to signIn; if agent knew the password, update the strength of
        # belief; analogously it works if user did not know the password.
        # Finally, if failed, repeat the sign in process with the updated beliefs
        login_response = self.sendAction('signIn', [service, username, password])
        if login_response[0] == 'success':
            self.num_logins += 1
            if service not in self.password_forget_rate:
                self.password_forget_rate[service] = self.initial_password_forget_rate
            else:
                self.password_forget_rate[service] /= self.forget_rate_discount  # from bruno_user.pl
            #if changed_password:
                #self.beliefs[service][2] += self.beliefs[service][2] * self.strengtheningRate
                #new_strength = min(self.beliefs[service][2], 0.9999)   # used to be 'max' but I think 'min' was intended
            self.beliefs[service] = [username, password, 1]
            print('signed into', service, 'with', 'changed' if changed_password else 'same', \
                  'username and password', username, ',', password, 'belief', belief)
            #else:
            #    self.beliefs[service] = [username, password, 1]
            #    print 'signed into', service, 'with same username and password', username, ',', password
            # Strengthen this password in all other services, and weaken all other passwords
            for s in self.beliefs:
                b = self.beliefs[service]  # [username, password, belief]
                if s != service and b[1] == password:
                    b[2] = min(1, b[2] + self.strengthen_factor * self.password_forget_rate[service])
            self.degrade_all_password_beliefs()
            return [{}]
        elif login_response[0] == 'failed:logged_in':
            self.degrade_all_password_beliefs()
            self.sign_out(service)
            return []
        else:
            # behavior from bruno_user.pl
            print('login response was', login_response, 'for', username, 'and', password, 'on', service, 'trying again')
            self.failed_logins += 1
            self.password_forget_rate[service] = self.password_forget_rate[service] * 2 * math.log(self.failed_logins)
            self.beliefs[service] = [username, password, 0]  # it is removed from the list in bruno_user.pl
            # If we had changed the password, change it back!
            if changed_password:
                self.beliefs[service] = [old_username, old_password, 0.65]  # the constant needs to be a parameter
            self.degrade_all_password_beliefs()
            #if changed_password:
            #    self.beliefs[service][2] -= (self.beliefs[service][2]*self.strengtheningRate)
            #    new_strength = max(self.beliefs[service][2], 0.0001)  # used to be 'min' but I think 'max' was intended
            #    self.beliefs[service] = [username, password, new_strength]
            return self.sign_in((goal, service))

    def degrade_all_password_beliefs(self):  # same as passwordFatigue in bruno_user.pl
        print('degrading beliefs:')
        for service in self.beliefs:
            b = self.beliefs[service]  # [username, password, belief]
            newb = max(0, b[2] - self.password_forget_rate[service])
            print('  ', service, 'from', b, 'to', newb)
            b[2] = newb

    def sign_out(self, args_tuple2):
        """ This should be equivalent to the signOut subgoal in prolog
        It checks if the user is logged in, and if so, it sends a message to log
        him out.

        Defined Actions:
            1. retrieveStatus
            2. signOut
        """
        (goal, service) = args_tuple2
        username = self.beliefs[service][0]
        response = self.sendAction('retrieveStatus', [service, username])
        if response[0] == 'failure':
            print('Error signing out: User was not logged in to', service, 'as', username)
            return []
        else:
            self.sendAction('signOut', [service, username])
            print('User successfully logged out from', service, 'as', username)
            return [{}]

    def reset_password(self, args_tuple3):
        #print 'Resetting: agent beliefs for service', service, 'are', self.beliefs[service]
        (goal, service) = args_tuple3
        self.num_reset_attempts += 1
        [username, old_password, belief] = self.beliefs[service]

        new_password = self.choose_password(username)

        status_response = self.sendAction('resetPassword', [service, username, old_password, new_password])

        if status_response[0] == 'success':
            self.num_resets += 1
            if new_password in self.writtenPasswords:
                self.beliefs[service] = [username, new_password, self.initial_belief, 0.999]
            else:
                self.beliefs[service] = [username, new_password, self.initial_belief]
            print('new beliefs for', service, 'after resetting:', self.beliefs[service])
            return [{}]
        else:
            #not yet implemented handling of requirements
            print('Reset password failed: Handle requirements')
            return []

    # Will be about password forget rate stopping criterion, but for now just false
    # This means the simulation will go on forever if the agent_Loop call doesn't use a finite number of steps
    def check_termination(self, call):
        # Would add here that the agent has a password forget rate below threshold for each known service
        # (from bruno_user.pl)
        return []

    # Extracted by Jim from setUpAccount and resetPassword, and modified to match the description in papers
    # such as the HotSoS 15 paper.
    def choose_password(self, username, requirements=None):
                ### choose Password
        # Note - this fails when the password_list is exhausted, which happens because passwords are moved
        # from this list to the knownPasswords list. I'm not sure what the correct behavior is here -
        # is it to choose something from that list when this one is empty? - Jim
        # I've added code below that uses the 'password_list' if there are still values on it, and otherwise picks
        # a known password.
        # This used to make a random choice, now it runs through the password_list in order, which is assumed
        # to be roughly in complexity order (added indices into password_list and known_passwords)
        list_of_new = self.password_list  # These are used with random choice, to pick without replacement
        list_of_old = self.known_passwords
        new_pw_index = 0
        old_pw_index = 0
        if list_of_new:
            if self.choose_password_method == 'random':
                desired_pass = random.choice(self.password_list)
                list_of_new = [x for x in list_of_new if x is not desired_pass]  # constructive, not surgical
            else:
                desired_pass = self.password_list[new_pw_index]  # random.choice(self.password_list)
                new_pw_index += 1
        elif self.known_passwords:
            if self.choose_password_method == 'random':
                desired_pass = random.choice(self.known_passwords)
                list_of_old = [x for x in list_of_old if x is not desired_pass]  # constructive not surgical
            else:
                desired_pass = self.known_passwords[old_pw_index]  # random.choice(self.known_passwords)
                old_pw_index += 1
        # if there are requirements verify that the password complies with them
        if requirements is not None:
            # will run through every unused password, then every used one, so maxTries is more of a timeout
            # for long lists
            max_tries = 100
            while (not requirements.verify(username, desired_pass) or self.over_cog_load(desired_pass)) and max_tries > 0:
                #print 'password', desired_pass, 'chosen from', len(list_of_new), len(list_of_old), \
                #    'not verified against', requirements
                if (self.choose_password_method == 'list-order' and new_pw_index < len(self.password_list)) or \
                        (self.choose_password_method == 'random' and list_of_new):
                    if self.choose_password_method == 'list-order':
                        desired_pass = self.password_list[new_pw_index]
                        new_pw_index += 1
                    else:
                        desired_pass = random.choice(list_of_new)
                        list_of_new = [x for x in list_of_new if x is not desired_pass]
                elif (self.choose_password_method == 'list-order' and old_pw_index < len(self.known_passwords)) or \
                        (self.choose_password_method == 'random' and list_of_old):
                    if self.choose_password_method == 'list-order':
                        desired_pass = self.known_passwords[old_pw_index]
                        old_pw_index += 1
                    else:
                        desired_pass = random.choice(list_of_old)
                        list_of_old = [x for x in list_of_old if x is not desired_pass]
                else:
                    break  # no more passwords to try
                max_tries -= 1

        # if pass is too hard, reuse the hardest one or write it down,
        # the decision is based on memoBias parameter
        # maybe add some distance heuristics later
        new_password_verified = (requirements is None or requirements.verify(username, desired_pass)) \
            and not self.over_cog_load(desired_pass)

        if new_password_verified:
            password = desired_pass
            # add to the list of known pass, and remove from potential passes
            if desired_pass not in self.known_passwords:
                self.known_passwords.append(desired_pass)
                # For now, compute and print the levenshtein set cost of the known passwords
                #print len(self.known_passwords), 'Levenshtein cost:', levenshtein_set_cost(self.known_passwords), self.known_passwords
            if desired_pass in self.password_list:
                self.password_list.remove(desired_pass)
            if username not in self.knownUsernames:
                self.knownUsernames.append(username)
        elif self.known_passwords and \
                (not new_password_verified or distPicker(self.memoBias, random.random()) == 'reuse'):
            # We have to reuse if we didn't find a good enough new password.
            #password = max(stats.iteritems(), key=operator.itemgetter(1))[0]
            # .. but actually we tried to reuse above, so we need to add something that synthesizes a password
            # here, e.g. adding numbers or characters if that is the problem, etc.

            # NOTE - this case happens all the time once we are at the cognitive limit, and picking the same
            # each time leads to more repeats than seem reasonable. Switching to random for now. Perhaps pick
            # randomly from those that satisfy the requirements, if any.
            #password = max(self.known_passwords, key=self.password_complexity)
            password = random.choice(self.known_passwords)
        else:
            password = desired_pass
            self.writtenPasswords.append(desired_pass)
            self.password_list.remove(desired_pass)
        print('choose password', password, '[', requirements, ']')
        return password

    # Boolean - whether adding the password as a new password will tip the agent over its cognitive load threshold
    def over_cog_load(self, password):
        if password in self.known_passwords:
            return False  # only increases the load if it's not already used
        else:
            new_cost = levenshtein_set_cost(self.known_passwords + [password])
            # Should also check username cost, but currently don't
            return new_cost > self.cognitive_threshold

    # Should return a measure of the complexity of the password by our usual standards.
    # Here I'm just using the length to get this up and running - and not sure this is what will be used finally
    # Could be static at present, but leaving it as a method so it can include agent parameters later.
    def password_complexity(self, password):
        return len(password)

    # System 1 neighbor rule:
    # Same passwords reinforce across services. Different passwords inhibit each other on one service.
    def link_password_nodes(self, node):
        (p, service, password) = node.fact
        for other in self.nodes:
            if other == node or not isinstance(other.fact, (tuple, list)) or not len(other.fact) > 2:
                continue
            elif other.fact[1] == service:
                node.add_neighbor(other, -1)
                other.add_neighbor(node, -1)
            elif other.fact[2] == password:
                node.add_neighbor(other, 1)
                other.add_neighbor(node, 1)
        #print 'linked', node

    # This is a measure that can be called on the agent at any time, returning the proportion of logins
    # where the agent also attempted to reset the password
    def proportion_of_resets(self):
        return float(self.num_resets)/self.num_login_attempts


# The cost of a set of strings is the cost of the minimum spanning tree over the set, with
# levenshtein distance as edge weight.
def levenshtein_set_cost(strings):
    # First create the graph (a complete graph)
    graph = {}
    for i in range(0, len(strings)):
        graph[i] = {}
        for j in range(0, len(strings)):
            if i < j:  # this will always come first
                graph[i][j] = levenshtein_distance(strings[i], strings[j])
            elif i > j:  # (so don't compute twice)
                graph[i][j] = graph[j][i]
    # Next compute the minimum spanning tree
    mst = minimum_spanning_tree(graph)
    return sum([graph[x][y] for (x,y) in mst])


# Copied from http://rosettacode.org/wiki/Levenshtein_distance
def levenshtein_distance(str1, str2):
    m = len(str1)
    n = len(str2)
    len_sum = float(m + n)
    d = []
    for i in range(m+1):
        d.append([i])
    del d[0][0]
    for j in range(n+1):
        d[0].append(j)
    for j in range(1,n+1):
        for i in range(1,m+1):
            if str1[i-1] == str2[j-1]:
                d[i].insert(j, d[i-1][j-1])
            else:
                minimum = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+2)
                d[i].insert(j, minimum)
    l_dist = d[-1][-1]
    #ratio = (len_sum - l_dist)/len_sum
    #return {'distance':l_dist, 'ratio':ratio}
    return l_dist

#print(levenshtein_distance("kitten","sitting"))
#print(levenshtein_distance("rosettacode","raisethysword"))


# This is replaced by pass_experiment.py
def run_one(hardnesses):
    pa = PasswordAgent()
    pa.sendAction('set_service_hardness', hardnesses)
    pa.agent_loop(100, disconnect_at_end=False)
    # Use the results on the hub, because the agent may create ids and passwords and then forget them,
    # but they still exist.
    #print 'final beliefs are', pa.beliefs
    #print len(pa.nodes), 'system 1 nodes:'
    #for node in sorted(pa.nodes, key=lambda n: pa.fact_to_key(n.fact)):
    #    print node
    # Read the number of reuses from the hub before disconnecting (could be computed here but aren't)
    reuses = pa.sendAction('send_reuses')
    pa.disconnect()
    print('reuses:', reuses)
    print('cog burden is', levenshtein_set_cost(pa.known_passwords), 'for', len(pa.known_passwords), \
          'passwords. Threshold is', pa.cognitive_threshold)
    return len(pa.known_passwords), expected_number_of_sites(reuses), reuses


# expected number of sites turned over (* p) based on prob attack of p and reuse prob of 1
def expected_number_of_sites(reuses):
    total = sum(i * v for i, v in reuses)  # each pair means v username/password combinations are used i times
    return sum([i*i*v for i, v in reuses])/float(total) if total > 0 else 0


if __name__ == "__main__":
    # Run one agent until quiescence (just for n steps until there is evidence of forgetting)
    pa = PasswordAgent()
    pa.agent_loop(500, disconnect_at_end=False)
    reuses = pa.sendAction('send_reuses')
    pa.disconnect()
    print(pa.num_login_attempts, 'login attempts', pa.num_logins, 'successful.', \
          pa.num_reset_attempts, 'reset attempts', pa.num_resets, 'successful.')
    print('reuses:', reuses)
    print('cog burden is', levenshtein_set_cost(pa.known_passwords), 'for', len(pa.known_passwords), \
       'passwords. Threshold is', pa.cognitive_threshold)
    print('known usernames is', pa.knownUsernames, 'passwords', pa.known_passwords)
    for m in pa.measures:
        print(m, m.eval(pa), "target: " + str(m.target) if m.target is not None else "")


# This ran a set of trials, now subsumed in pass_experiment.py
#if __name__ == "__main__":
#    results = []
#    for i in range(0, 14):
#        hardnesses = [['weak', 1 + i, i/6, 0.33], ['average', 5+i, i/4, 0.67], ['strong', 8+i, i/3, 1.0]]
#        print hardnesses
#        local_result = [run_one(hardnesses) for trial in xrange(1, 30)]
#        results.append((i, local_result, hardnesses))
#        print i, 'ave n', sum(r[0] for r in local_result)/float(len(local_result))
#        print i, 'ave r', sum(r[1] for r in local_result)/float(len(local_result))
#    for [i, local_result, h] in results:
#        print i, 'ave n', sum(r[0] for r in local_result)/float(len(local_result))
#        print i, 'ave r', sum(r[1] for r in local_result)/float(len(local_result))

# what I used
#for [i, local_result, h] in results:
#     This is a weighted sum of the hardness and the estimated probability that a site is safe from a reuse attack
#     (9 sites were used for these runs)
#     print min((i * 0.2 + sum(9 - r[1] for r in local_result)/float(len(local_result))) / 9, 1.0)
