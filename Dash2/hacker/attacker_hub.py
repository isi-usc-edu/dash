# A hub that supports a range of attacks from attacker.py and maintains the state of a network of computers.
# The attacker can mount real attacks in a framework like DETER but this should be used otherwise to avoid
# dangerous or suspicious activity.
import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub


# The Computer class keeps track of hostname, reachability and what services are running on what ports.
# It will ultimately also keep track of installed software and patches, users logged on and processes.
class Computer:
    def __init__(self, hostname, reachable=[], services={}):
        self.hostname = hostname  # Should probably have IP address and a look-up table, will fix one day
        self.reachable = reachable  # other computers reachable from this one
        self.services = services  # services are pairs (port, service_name), e.g. (80, _http)


class AttackerHub(WorldHub):

    def __init__(self):
        WorldHub.__init__(self)
        # The network is a dict of computers by name that can be initialized and set up by other agents.
        # Each computer includes a list of other computers it can reach on the network. This is used
        # to support private networks and pivoting attacks.
        self.network = {          # Set up the default network assumed in the original example attack
          'localhost': Computer('localhost', reachable=['server1', 'server2', 'server3']),
          'server1': Computer('server1', reachable=['server2', 'server3'], services={80: 'http'}),
          'server2': Computer('server2', reachable=['server1', 'server3'], services={80: 'http'}),
          'server3': Computer('server3', reachable=['server1', 'server2', 'hidden_computer'], services={80: 'http'}),
          'hidden_computer': Computer('hidden_computer', reachable=['server3'], services={80: 'http'}),
        }

    # Scan for computers connected to the current computer
    def host_scanner(self, agent_id, executable_host):
        # It's up to the agent to ensure it can actually run a scan from the host machine
        (executable, host) = executable_host
        if host[1:] in self.network:
            return 'success', self.network[host[1:]].reachable
        else:
            return 'fail'

    def port_scanner(self, agent_id, executable_host_target):
        # For now ignore the executable and host, assume it works and that target is a constant,
        # and return the services for the matching target machine
        (executable, host, target) = executable_host_target
        if target[1:] in self.network:
            return 'success', self.network[target[1:]].services
        else:
            return 'fail', 'no such host:', target, 'or target is not reachable from', host

    def check_sql_vulnerability(self, agent_id, action):
        print('checking sql vulnerability with arguments', action)
        return 'success'

    def sql_injection_read_file(self, agent_id, action):
        return 'success', 'these are the file contents'

if __name__ == "__main__":
    AttackerHub().run()
