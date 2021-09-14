# Initial attacker agent for password agents
import sys; sys.path.extend(['../../'])
import random
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isVar


class PasswordAgentAttacker(DASHAgent):

    #probability that a an attacker will reuse passwords across services
    #percentage taken from Bruno's prolog version
    reuseRisk = 0.40

    #scalar to determin probability that a password is vulnerable
    #scalar taken from Bruno's prolog version
    inherentRisk = 0.2

    def __init__(self):
        DASHAgent.__init__(self)
        self.readAgent("""

goalWeight attack 1

# The agent prefers an indirect attack if possible since it is perhaps cheaper
goalRequirements attack
    chooseAttack(_indirect)
    findUncompromisedSite(site)
    findCompromisedSite(comp)
    reusePassword(comp, site)
    forget([chooseAttack(x), findUncompromisedSite(x), findCompromisedSite(x), reusePassword(x,y)])

goalRequirements attack
    chooseAttack(_direct)
    findUncompromisedSite(site)
    directAttack(site)
    forget([chooseAttack(x), findUncompromisedSite(x), directAttack(x)])

# If chooseAttack fails in both clauses (since the calls are independent), just try again as long as there's
# something left to attack
goalRequirements attack
    findUncompromisedSite(site)
    forget([chooseAttack(x), findUncompromisedSite(x), directAttack(x), reusePassword(c, s), findCompromisedSite(x)])

transient attack

""")
        self.primitiveActions([('findUncompromisedSite', self.find_unc_site), ('directAttack', self.direct_attack),
                               ('chooseAttack', self.choose_attack), ('findCompromisedSite', self.find_compromised_site),
                               ('reusePassword', self.reuse_password)])
        self.register()     # Register with the running password agent hub

        # These are sets since the main operations are set difference and adding or removing elements
        self.uncompromised_sites = set() #['bank1', 'bank2', 'mail1', 'mail2', 'amazon', 'youtube']
        self.compromised_sites = set()  # If a site is compromised, I guess we assume the attacker knows all user/pwd combos there
        self.failed = []
        self.failed_direct = 0
        self.successful_direct = 0
        self.failed_indirect = 0
        self.successful_indirect = 0

        #self.traceAction = True
        #self.traceGoals = True

    # At the end of a run, print out how many successful and failed direct and indirect attacks took place
    def printStatistics(self):
        print(('direct:', self.successful_direct, 'successful,', self.failed_direct, 'failed'))
        print(('indirect:', self.successful_indirect, 'successful,', self.failed_indirect, 'failed'))

    # Decide which style of attack to try next. Binds the main variable to either _direct or _indirect
    def choose_attack(self, goal_term):
        (goal, term) = goal_term
        if term == "_direct":
            if not self.compromised_sites or (random.random() > self.reuseRisk):
                print('making a direct attack')
                return [{}]
            else:
                return []
        elif term == "_indirect":
            if self.compromised_sites and (random.random() < self.reuseRisk):
                print('making an indirect attack')
                return [{}]
            else:
                return []
        elif isVar(term):
            if not self.compromised_sites:
                print('choosing direct attack since there are no compromised sites')
                return [{term: '_direct'}] # Must choose direct if no sites are compromised yet
            elif random.random() > self.reuseRisk:   #
                print(('choosing direct attack (', (1 - self.reuseRisk), 'chance)'))
                return [{term: '_direct'}]
            else:
                print(('choosing indirect attack (', self.reuseRisk, 'chance)'))
                return [{term: '_indirect'}]
        else:  # some constant that is not an attack style
            return []

    # Bind the site variable to a random possible site to attack.
    # Ultimately, get the names from the hub and keep track of those that have already been compromised
    # or where the agent has failed, and attack the rest.
    # For now, use an internal list of sites
    def find_unc_site(self, goal_sitevar):
        (goal, site_var) = goal_sitevar
        [status, data] = self.sendAction('listAllSites')
        # This call is made every time in case new sites have been added in the hub. Filter out the ones
        # that are already compromised (using set difference). Return a list of bindings, one for each possible site.
        self.uncompromised_sites = set(data) - self.compromised_sites
        print(('uncompromised sites: ', self.uncompromised_sites, 'compromised sites', self.compromised_sites))
        return [{site_var: unc_site} for unc_site in self.uncompromised_sites]

    def find_compromised_site(self, goal_site):
        # Keep track internally of what was compromised (from the hub's point of view, someone logged in to a site,
        # but the agent knows this was a password reuse attack).
        #[status, data] = self.sendAction('findCompromisedSite')
        # Return a list of bindings, one for each possible compromised site.
        (goal, site_var) = goal_site
        return [{site_var: compromised_site} for compromised_site in self.compromised_sites]

    def direct_attack(self, goal_site):   # call is (directAttack, site)
        (goal, site) = goal_site
        status = self.sendAction('directAttack', [site])   # action just returns success or failure
        if status == 'success':
            self.uncompromised_sites.remove(site)
            self.compromised_sites.add(site)
            self.successful_direct += 1
            return [{}]   # Success with empty bindings
        else:
            self.failed_direct += 1
            return []

    def reuse_password(self, goal_comp_site):    # call is (reusePassword, comp, site)
        (goal, comp, site) = goal_comp_site
        [status, list_of_pairs] = self.sendAction('getUserPWList', [comp])   # will fail if site wasn't compromised
        # Pick a pair at random and try to log in (low success rate)
        if status == 'success' and list_of_pairs:
            (user, password) = random.choice(list_of_pairs)
            status = self.sendAction('signIn', [site, user, password])
            if status[0] == 'success':
                self.uncompromised_sites.remove(site)
                self.compromised_sites.add(site)
                print(('successfully reused', user, password, 'from', comp, 'on', site))
                self.successful_indirect += 1
                return [{}]
            else:
                print(('failed attempt to reuse', user, password, 'from', comp, 'on', site))
                self.failed_indirect += 1
                return []
        else:
            print(('site', comp, 'was not compromised after all or there were no users'))
            return []


if __name__ == "__main__":
    pa = PasswordAgentAttacker()
    pa.agent_loop()    # ends when all the sites are compromised
    pa.printStatistics()
