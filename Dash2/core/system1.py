# Contains code managing instinctive behavior and spreading activation

# In the first iteration, system 1 has a set of nodes, which have facts and activation strengths.
# Facts take the same form as predicates in system 2 and allow unification with activation rules.
# Each node is updated and may update its neighbors once per iteration. Nodes with high enough
# activation may affect system2 reasoning, or override it if the node chooses an action to
# perform.


class Node:
    default_decay = 0.1  # activation goes down by this much each cycle in the absence of spreading activation

    def __init__(self, node_id, fact, activation=0, valence=0, decay=default_decay, neighbors=None):
        self.node_id = node_id
        self.fact = fact
        self.decay = decay
        self.activation = activation
        self.valence = valence
        # neighbors is a list of pairs (node, link_strength)
        self.neighbors = [] if neighbors is None else neighbors
        # This keeps track of whether activation should be passed to neighbors so we don't loop
        self.change_since_update = 0

    def __str__(self):
        return "N" + str(self.node_id) + ": " + str(self.fact) + ", " + str(self.activation)\
               + ", " + str([link[0].node_id for link in self.neighbors])

    def __repr__(self):
        return self.__str__()

    def update(self, activation_increment):
        self.activation += activation_increment
        if self.activation < 0:
            self.activation = 0
        self.change_since_update += activation_increment

    def spread(self):
        if self.change_since_update != 0:
            for neighbor in self.neighbors:
                neighbor[0].update(self.change_since_update/3 * neighbor[1])
            self.change_since_update = 0

    def apply_decay(self):
        self.update(0 - self.decay)

    # link_strength says how the neighbor is affected by changes to this node. Currently using just +/- 1
    # to designate a positive or negative connection, but the link magnitude is also used in spreading.
    def add_neighbor(self, node, link_strength=1):
        self.neighbors.append((node, link_strength))

    def node_to_action(self):
        if self.fact[0] == 'action':
            return self.fact[1:]
        else:
            return 0


class System1Agent:

    def __init__(self):
        self.system1Fact = set()
        self.nodes = set()
        self.action_nodes = set()  # subset of nodes that suggest an action, for efficiency
        self.fact_node_dict = dict()  # maps node facts to nodes
        self.neighbor_rules = dict()  # maps node fact predicates to lambdas
        self.trace_add_activation = False
        # Activation threshold at which actions suggested by system 1 will be considered over deliberation
        # A low threshold will produce more 'impulsive' actions
        self.system1_threshold = 0.1

    # Interface allows for alternative system 1 approaches, while this default version performs spreading activation
    def system1_update(self):  # apply newly learned information to update the state of system 1
        self.spreading_activation()

    def system1_step(self):  # Evolve the state by one step in the absence of new information
        self.system1_decay()

    def system1_propose_actions(self):  # propose actions to take
        action_nodes = self.actions_over_threshold(threshold=self.system1_threshold)
        if action_nodes:
            return [a.node_to_action() for a in action_nodes]
        else:
            return []


    # The methods below this point are specific to spreading activation

    # Main DASH agent communicates activation for a fact. This looks up the node with fact_node_dict, adding
    # if necessary, and increments the activation
    def add_activation(self, fact, activation_increment=0.3):
        n = self.fact_to_node(fact)
        if self.trace_add_activation:
            print('adding activation to', n)
        n.update(activation_increment)

    def spreading_activation(self):
        for node in self.nodes:
            node.spread()

    def system1_decay(self):
        for node in self.nodes:
            node.apply_decay()

    def nodes_over_threshold(self, threshold=0.5):
        return [n for n in self.nodes if n.activation >= threshold]

    def actions_over_threshold(self, threshold=0.5):
        return [n for n in self.action_nodes if n.activation >= threshold]

    # Turn a fact into a unique key by writing brackets and elements into a string
    # so ('hi', ('there', 'you')) becomes "[hi[there,you]]"
    def fact_to_key(self, fact):
        if isinstance(fact, (list, tuple)):
            result = "["
            for sub_fact in fact:
                result += ("," if len(result) > 1 else "") + self.fact_to_key(sub_fact)
            return result + "]"
        else:
            return str(fact)

    # Given a fact, return its node, creating a new one if needed.
    def fact_to_node(self, fact):
        key = self.fact_to_key(fact)
        if key not in self.fact_node_dict:
            node = Node(len(self.nodes) + 1, fact)
            self.fact_node_dict[key] = node
            self.nodes.add(node)
            self.create_and_link_neighbors(node)
            if fact[0] == 'action':
                self.action_nodes.add(node)
        return self.fact_node_dict[key]

    # Apply neighbor creation rules to create or link nodes
    def create_and_link_neighbors(self, node):
        if node.fact[0] in self.neighbor_rules:
            for rule in self.neighbor_rules[node.fact[0]]:
                rule(node)

    # Create a spreading activation rule, that sets up neighbors for nodes that match the rule
    # and reinforcement strengths.
    def create_neighbor_rule(self, node_pattern, action):
        if node_pattern not in self.neighbor_rules:
            self.neighbor_rules[node_pattern] = []
        self.neighbor_rules[node_pattern].append(action)
