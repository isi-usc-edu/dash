from collections import namedtuple
from collections import deque
from copy import copy
from random import Random
from math import exp


Concept_ = namedtuple('Concept', ['name', 'id'])


class Concept(Concept_):
    """
    An immutable object representing a concept w/ name and id.
    name and id are not actually used here in the module.
    Any object that is hashable, immutable, and has __eq__, can be used as a
    concept.
    """
    __slots__ = ()


class ConceptPair(tuple):
    """
    An immutable object representing a pair of concepts.
    Concepts can be any hashable/immutable type with __eq__ defined.
    Elements can be independently accessed but is still hashable and 
    order doesn't matter: 
    E.g. ConceptPair(concept1,concept2) == ConceptPair(concept2,concept1)

    ConceptPairs are used as keys for Beliefs.
    """
    __slots__ = ()
    def __new__(cls, concept1, concept2):
        return tuple.__new__(cls, (concept1, concept2))

    @property
    def concept1(self):
        return tuple.__getitem__(self, 0)

    @property
    def concept2(self):
        return tuple.__getitem__(self, 1)

    def __getitem__(self, item):
        raise TypeError

    def __eq__(self, other):
        """
        A belief is equivalent to another if both of its concepts are the
        same. Even though it is a tuple underneath, there is no element order
        """

        return ((tuple.__getitem__(self, 0) == other.concept1) and 
                (tuple.__getitem__(self, 1) == other.concept2)) or \
               ((tuple.__getitem__(self, 0) == other.concept2) and 
                (tuple.__getitem__(self, 1) == other.concept1))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(frozenset(self))


class ConceptTriad(tuple):
    """
    An immutable object that represents a triangle, of three concepts.
    Concepts can be any hashable/immutable type with __eq__ defined.
    Internally it is represented as 3 ConceptPairs.
    Elements can be independently accessed but are 
    still hashable and order doesn't matter: 
    E.g. ConceptTriad(concept1,concept2,concept3) ==
         ConceptTriad(concept2,concept3,concept1)

    ConceptTriads are a convenient way to store concept-pair and concept
    information for calculating the internal energy, checking for triangles,
    or looking-up specific Beliefs.
    """
    __slots__ = ()
    def __new__(cls, concept1, concept2, concept3):
        return tuple.__new__(cls, (ConceptPair(concept1, concept2), 
                                   ConceptPair(concept2, concept3), 
                                   ConceptPair(concept3, concept1)))

    @property
    def pair1(self):
        return tuple.__getitem__(self, 0)

    @property
    def pair2(self):
        return tuple.__getitem__(self, 1)

    @property
    def pair3(self):
        return tuple.__getitem__(self, 2)

    def __getitem__(self, item):
        raise TypeError

    def __eq__(self, other):
        """
        A belief is equivalent to another if both of its concepts are the
        same. Even though it is a tuple underneath, there is no element order
        """

        return ((tuple.__getitem__(self, 0) in other) and
                (tuple.__getitem__(self, 1) in other) and
                (tuple.__getitem__(self, 2) in other))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(frozenset(self))


class Beliefs(dict):
    """
    An object that represents a set of beliefs. It also doubles as a vector.
    Currently implements dot product. If needed, add support for other
    math operations.

    There are no 'scalar' beliefs, so a single belief is represented as a
    single element vector.

    Beliefs subclasses dict, so it has access to all the functions dict provides
    and can be instantiated in the same fashion.
    """

    def __init__(self, *args):
        """
        Can be initialized with a dictionary keyed by ConceptPairs and valued
        by valences
        """
        dict.__init__(self, *args)

    def __str__(self):
        """
        A more nicely formatted version of the dict string. One belief per line
        :return: string
        """

        out_str = ""
        for concept_pair, valence in self.items():
            out_str += "\t" + str(concept_pair) + "\t" + str(valence) + "\n"
        return out_str

    def add_belief(self, concept_pair, valence):
        """
        Adds a belief to the
        :param concept_pair: A ConceptPair like object
        :param valence: A numeric value
        """
        dict.__setitem__(self, concept_pair, valence)

    def __mul__(self, other):
        """
        This implements the dot product between two sets of beliefs.
        The operation is only carried out such that the overlapping subset of 
        beliefs that belong to both sets will contribute to the product.
        It only makes sense this way as non-overlapping elements would 
        multiply to 0 and not contribute to the sum.

        If a scalar is used, it multiplies the all valences by the scalar.
        """
        if isinstance(other, BeliefNetwork):
            dot_product = 0.0
            for other_pair, other_valence in other.beliefs.items():
                if other_pair in self:
                    dot_product += self.__getitem__(other_pair) * other_valence
            return dot_product

        elif isinstance(other, Beliefs):
            dot_product = 0.0
            for other_pair, other_valence in other.items():
                if other_pair in self:
                    dot_product += self.__getitem__(other_pair) * other_valence
            return dot_product

        else:
            # Scalar case
            for belief in self.keys():
                self[belief] *= other
            return self

    def __hash__(self):
        return hash(frozenset({frozenset({key, value})
                               for key, value in self.items()}))

    # Ensure commutivity of dot product
    __rmul__ = __mul__


class BeliefNetwork(object):
    """
    Nodes represent concepts in the belief network and edges represent a
    valenced relationship between those concepts. The valence can be positive or
    negative. No connection means no relationship. Triads of beliefs are
    checked for stability:
        +++ is stable
        -++ is unstable
        --+ is stable
        --- is unstable
    Edges can be weighted (e.g. valence). The product of the weights specifies
    triad stability. Given a set triad with valences a_i, a_j, and a_k, the
    energy is given by:

        triad energy = - a_i * a_j * a_k

    Lower energy corresponds to higher coherence of beliefs.

    A BeliefNetwork can be modified in-place via addition with another
    belief networks or Beliefs through the += or -= operators. Scalar values
    can also be add/subtracted from the valences of the entire vector. Dot
    product is also supported with *. However, * used with a scalar carries
    out normal multiplication. Add additional operators if needed.

    The energy of the belief network is the internal energy, not to be confused
    with the social energy.
    """

    def __init__(self, beliefs=None):
        """
        beliefs - A Beliefs type (0 or more beliefs) [no copy is made]
        """

        if beliefs is None:
            beliefs = Beliefs()

        self.beliefs = beliefs
        self.concept_set = self._find_all_concepts(self.beliefs.keys())
        self.triangle_set = self._find_all_triangles(self.beliefs.keys(), 
                                                     self.beliefs,
                                                     self.concept_set)
        self.energy = self._calc_energy(self.triangle_set, self.beliefs)

    def __str__(self):

        return str(self.beliefs)

    def __iadd__(self, other):
        """
        In place addition. If adding a belief network or beliefs, then
        valences are added to the respective pairs. If a pair doesn't
        exist, then it is initialized to 0 and the addition continues. 
        If adding a scalar, then scalar is added to valences of all pairs.
        The energy is updated after the 
        """
        if isinstance(other, BeliefNetwork):
            for concept_pair, valence in other.beliefs.items():
                if concept_pair in self.beliefs:
                    self.beliefs[concept_pair] += valence
                else:
                    self.add_belief(Beliefs({concept_pair: valence}), False)

            self.update_energy()
            return self

        elif isinstance(other, Beliefs):
            for concept_pair, valence in other.items():
                if concept_pair in self.beliefs:
                    self.beliefs[concept_pair] += valence
                else:
                    self.add_belief(Beliefs({concept_pair: valence}), False)

            self.update_energy()
            return self

        else:
            # Scalar case
            for belief in self.beliefs.keys():
                self.beliefs[belief] += other

            self.update_energy()
            return self

    def __isub__(self, other):
        """
        In place subtraction. If adding a belief network or beliefs, then
        valences are subtracted from the respective pairs. If a pair doesn't
        exist, then it is initialized to 0 and the subtraction continues. 
        If adding a scalar, then scalar is subtracted from valences of all pairs.
        """
        if isinstance(other, BeliefNetwork):
            for concept_pair, valence in other.beliefs.items():
                if concept_pair in self.beliefs:
                    self.beliefs[concept_pair] -= valence
                else:
                    self.beliefs[concept_pair] = -valence
                    self.add_belief(Beliefs({concept_pair: -valence}), False)

            self.update_energy()
            return self

        elif isinstance(other, Beliefs):
            for concept_pair, valence in other.items():
                if concept_pair in self.beliefs:
                    self.beliefs[concept_pair] -= valence
                else:
                    self.add_belief(Beliefs({concept_pair : -valence}), False)

            self.update_energy()
            return self

        else:
            # Scalar case
            for belief in self.beliefs.keys():
                self.beliefs[belief] -= other

            self.update_energy()
            return self

    def __mul__(self, other):
        """
        This implements the dot product between two sets of beliefs.
        The operation is only carried out such that the overlapping subset of 
        beliefs that belong to both sets will contribute to the product.
        It only makes sense this way as non-overlapping elements would 
        multiply to 0 and not contribute to the sum.

        If a scalar is used, it multiplies the all valences by the scalar.
        """
        if isinstance(other, BeliefNetwork):
            dot_product = 0.0
            for other_pair, other_valence in other.beliefs.items():
                if other_pair in self.beliefs:
                    dot_product += self.beliefs[other_pair] * other_valence
            return dot_product

        elif isinstance(other, Beliefs):
            dot_product = 0.0
            for other_pair, other_valence in other.items():
                if other_pair in self.beliefs:
                    dot_product += self.beliefs[other_pair] * other_valence
            return dot_product

        else:
            # Scalar case
            for belief in self.beliefs.keys():
                self.beliefs[belief] *= other
            return self

    # Ensure commutativity of dot product
    __rmul__ = __mul__

    def _find_all_concepts(self, beliefs):
        """
        Generates a list of nodes in the network (also known as concepts)
        """
        return set([concept for concept_pair in beliefs
                    for concept in list(concept_pair)])

    def _find_all_triangles(self, concept_pairs, belief_set, concept_set):
        """
        Generates a set of triangles in the network
        :param concept_pairs: A sequence/set of pairs (keys of belief_set)
        :param belief_set: a Beliefs type object that represents the network you
            want to search over
        :param concept_set: set/sequence of concepts
        :return a set of all triads found in network, as ConceptTriad
        """
        triangle_set = set()
        for concept_pair in concept_pairs:
            new_triangles = self._find_triangles_with_concept_pair(concept_pair,
                                triangle_set, belief_set, concept_set)
            triangle_set.update(new_triangles)

        return triangle_set

    def _find_triangles_with_concept_pair(self, concept_pair, triangle_set, 
                                          belief_set, concept_set):
        """
        finds triangles that have the concept pair as a link
        :param concept_pair: a ConceptPair like object
        :param triangle_set: a set of triads to check against redundancy
        :param belief_set: a hash of pairs to check for triad
        :param concept_set: set/sequence of concepts
        :return A set of new triads
        """
        new_triangles = set()
        for concept in concept_set:
            if ConceptPair(concept_pair.concept1, concept) in belief_set \
            and ConceptPair(concept_pair.concept2, concept) in belief_set:
                triangle = ConceptTriad(concept_pair.concept1, 
                                        concept_pair.concept2, concept)
                if triangle not in triangle_set:
                    new_triangles.add(triangle)

        return new_triangles

    def _calc_energy(self, triad_sequence, beliefs):
        """
        :param triad_sequence: A sequence of triad like objects
        :param beliefs: beliefs like object
        :return: energy contribution of all triads in the sequence
        """
        energy = 0.0
        for triad in triad_sequence:
            energy += self._triad_energy_contribution(triad, beliefs)

        return energy

    def _triad_energy_contribution(self, triad, beliefs):
        """
        :param triad: A triad like object
        :param beliefs: A beliefs like object
        :return: energy of the specific triad
        """
        return -beliefs[triad.pair1] \
                * beliefs[triad.pair2] \
                * beliefs[triad.pair3]

    def _add_concepts(self, concept_pair):
        """
        Checks and adds concepts to the necessary containers.
        :param concept_pair:
        :return: None
        """
        if concept_pair.concept1 not in self.concept_set:
            self.concept_set.add(concept_pair.concept1)
        if concept_pair.concept2 not in self.concept_set:
            self.concept_set.add(concept_pair.concept2)

    def add_belief(self, belief, update_energy=True):
        """
        add belief to network, overwriting current belief.
        Updates the internal energy by default
        :param belief: A Beliefs (one or more)
        :param update_energy: True/False
        :return None
        """

        for concept_pair, valence in belief.items():
            if concept_pair in self.beliefs:
                if self.beliefs[concept_pair] != valence:
                    self.beliefs[concept_pair] = valence
                    if update_energy:
                        self.energy = self._calc_energy(self.triangle_set,
                                                        self.beliefs)
            else:
                self.beliefs[concept_pair] = valence
                new_triangles = self._find_triangles_with_concept_pair(concept_pair,
                    self.triangle_set, self.beliefs, self.concept_set)
                self._add_concepts(concept_pair)
                self.triangle_set.update(new_triangles)
                if update_energy:
                    self.energy += self._calc_energy(new_triangles, self.beliefs)

    def add_concept_pair(self, concept_pair, update_energy=True):
        """
        Adds a pair of concepts to the beliefs.
        If the pair doesn't exist already, the valence is initialized to 0.
        Updates the internal energy.
        Does nothing but update energy if the pair already exists.
        :param concept_pair: a ConceptPair type
        :param update_energy: True/False
        :return: None
        """
        if concept_pair not in self.beliefs:
            self.add_belief(Beliefs({concept_pair : 0.0}), update_energy)

    def update_energy(self):
        """
        Recalculates the energy given the current state of the network
        """

        self.energy = self._calc_energy(self.triangle_set, self.beliefs)

    def __copy__(self):
        """
        Make a fast copy that by-passes the expensive __init__ function of
        the belief network. Uses an empty_copy function that carries out this
        __init__ by-pass
        """
        newcopy = empty_copy(self)
        newcopy.beliefs = copy(self.beliefs)
        newcopy.concept_set = copy(self.concept_set)
        newcopy.triangle_set = copy(self.triangle_set)
        newcopy.energy = self.energy
        return newcopy

    def __contains__(self, item):
        """
        Implemented for use with 'in' operator
        :param item: either a Beliefs or a ConceptPair. If Beliefs, it will
            iterate over each Belief and check that the ConceptPair and
            valence match what is in the network. If it is a ConceptPair, then
            it just checks if the concept is in the network.
        :return: True/False
        """

        if isinstance(item, Beliefs):

            for pair, valence in item.items():
                if pair not in self.beliefs:
                    return False
                elif self.beliefs[pair] != valence:
                    return False

            return True

        elif isinstance(item, ConceptPair):
            return item in self.beliefs

        else:
            raise NotImplementedError


def empty_copy(obj):
    """
    Subclass object and overwrite __init__ function to by-pass expensive
    initialization functions.
    """
    class Empty(obj.__class__):
        def __init__(self): pass
    newcopy = Empty()
    newcopy.__class__ = obj.__class__
    return newcopy


class BeliefModule(object):
    """
    Represents a cognitive module for assessing the coherence of an agents
    belief system. It handles receiving (listen) and sending (talk) beliefs,
    updating the belief network of the agent, and determining whether to 
    accept or reject new beliefs.

    Shallow copy access to the underlying beliefs of both the beliefs
    and perceived beliefs is given via the beliefs and perceived_beliefs
    properties. Alternatively, direct access to those items can be achieved
    via .belief_network.beliefs or .perceived_belief_network.beliefs
    """
    def __init__(self, **kwargs):
        """
        :param belief_net: a BeliefNetwork type object. default=BeliefNetwork()
        :param perceived_net: a BeliefNetwork type object representing the agent's
            perception of other's beliefs. default=BeliefNetwork()
        :param seed: seed number for internal rng (uses Random). default=1
        :param max_memory: how many steps back the agent remembers incoming beliefs.
            This can be used in methods for outputing popular/recent beliefs.
            default=1
        :param T: Higher T will increase the likelihood of accepting beliefs that would
            increase the agents energy. default=1.0
        :param J: coherentism, controls contribution of internal belief system energy to
            total energy. default=1.0
        :param I: peer-influence, controls contribution of social energy to the total
            energy. default=1.0
        :param tau: float between [1,inf]. Higher values prefer older beliefs
            and reduce the contribution of newer beliefs to perceived beliefs.
            default=1.0
        :param recent_belief_chance: [0,1], the probability of choosing a belief to
            emit from short-term memory. If a recent belief isn't chosen, then
            a belief is chosen uniformly at random from the belief network.
            default=0.0
        :param verbose: prints talking/decision information
        """
        self.belief_network = kwargs.get("belief_net", BeliefNetwork())
        self.perceived_belief_network = kwargs.get("perceived_net", BeliefNetwork())
        self._max_memory = kwargs.get("max_memory", 1)
        self._memory = deque(maxlen=self._max_memory)
        self._seed = kwargs.get("seed", 1)
        self._rng = Random(self._seed)
        self.recent_belief_chance = kwargs.get("recent_belief_chance", 0.0)
        self.T = kwargs.get("T", 1.0)
        self.J = kwargs.get("J", 1.0)
        self.I = kwargs.get("I", 1.0)
        self.tau = kwargs.get("tau", 1.0)
        self.verbose = kwargs.get("verbose", False)

    @property
    def beliefs(self):
        """
        :return: shallow copy of own Beliefs
        Original can be accessed via belief_network.beliefs
        """

        return copy(self.belief_network.beliefs)

    @beliefs.setter
    def beliefs(self, value):
        raise AssertionError("Not allowed to set beliefs")

    @property
    def perceived_beliefs(self):
        """
        :return: shallow copy of perceived Beliefs
        Original can be accessed via perceived_belief_network.beliefs
        """

        return copy(self.perceived_belief_network.beliefs)

    @perceived_beliefs.setter
    def perceived_beliefs(self, value):
        raise AssertionError("Not allowed to set perceived beliefs")

    def __str__(self):
        """
        Converts attributes/beliefs/memory/energy into str
        :return: string
        """
        out_str = "BeliefModule attributes:\n"
        out_str += "\tT: " + str(self.T) + "\n"
        out_str += "\tJ: " + str(self.J) + "\n"
        out_str += "\tI: " + str(self.I) + "\n"
        out_str += "\ttau: " + str(self.tau) + "\n"
        out_str += "\tmax mem: " + str(self._max_memory) + "\n"
        out_str += "\trecent_belief_chance: " \
                   + str(self.recent_belief_chance) + "\n\n"
        out_str += "Memory:\n"
        out_str += "\t" + str(self._memory) + "\n"
        out_str += "\nOwn Beliefs: energy = " \
                   + str(self.belief_network.energy) + "\n"
        out_str += str(self.belief_network)
        out_str += "\nPerceived Beliefs: energy = " \
                   + str(self.perceived_belief_network.energy) + "\n"
        out_str += str(self.perceived_belief_network)
        return out_str

    def seed(self, integer):
        """
        re-seeds rng
        :param integer: an integer value for the seed
        """
        self._rng.seed(integer)
        self._seed = integer

    def _is_belief_acceptable(self, belief):
        """
        Given a belief(s) will return True if acceptable else False.
        Creates a shallow copy of the belief network and adds the new belief(s)
        to calculate the internal and social energy of a candidate belief(s).
        If the belief(s) would lower the total energy it is accepted, else it
        is accepted with some probability.
        """

        current_social_energy = -(self.belief_network *
                                  self.perceived_belief_network)
        current_total_energy = self.J * self.belief_network.energy + \
                               self.I * current_social_energy

        candidate_belief_net = copy(self.belief_network)
        candidate_belief_net.add_belief(belief)
        candidate_social_energy = -(candidate_belief_net *
                                    self.perceived_belief_network)

        candidate_total_energy = self.J * candidate_belief_net.energy + \
                                 self.I * candidate_social_energy

        if candidate_total_energy <= current_total_energy:
            if self.verbose:
                print("candidate_energy: ", candidate_total_energy,
                      "current_energy", current_total_energy,
                      'DECISION: Accept')
            return True

        else:
            rng_roll = self._rng.random()
            accept_prob = exp((current_total_energy - candidate_total_energy) / self.T)
            if accept_prob > rng_roll:
                if self.verbose:
                    print("candidate_energy: ", candidate_total_energy,
                          "current_energy", current_total_energy,
                          "accept prob", accept_prob,
                          "roll", rng_roll,
                          'DECISION: Accept')
                return True

            else:
                if self.verbose:
                    print("candidate_energy: ", candidate_total_energy,
                          "current_energy", current_total_energy,
                          "accept prob", accept_prob,
                          "roll", rng_roll,
                          'DECISION: Reject')
                return False

    def _add_belief_to_memory(self, belief):
        """
        Adds an accepted belief(s) to memory
        If memory would exceed its maximum capacity the oldest memory
        is dropped from the deque
        """

        if len(self._memory) < self._max_memory:
            self._memory.append(belief)
        else:
            self._memory.popleft()
            self._memory.append(belief)

    def _update_perceived_beliefs(self, belief):
        """
        See documentation for explanation of update equation
        summary: belief valences of perceived beliefs move closer to the
        input belief
        """

        for concept_pair, valence in belief.items():
            # Adding the pair sets up a 0 initialized valence belief
            self.perceived_belief_network.add_concept_pair(concept_pair)
            current_valence = self.perceived_belief_network.beliefs[concept_pair]
            self.perceived_belief_network.beliefs[concept_pair] += 1. / self.tau * (
                valence - current_valence)

    def emit_belief(self):
        """
        chooses and emits a belief from belief network from memory or from
        their belief network
        :return A single element Beliefs object
        """

        if (self._rng.random() < self.recent_belief_chance) \
                and (len(self._memory) != 0):
            if self.verbose:
                print("Drawing from memory")
            return self._rng.choice(self._memory)
        else:
            if self.verbose:
                print("Drawing from beliefs")
            return Beliefs((self._rng.choice(self.belief_network.beliefs.items()),))

    def process_belief(self, belief):
        """
        evaluates veracity of incoming belief(s)
        if the agent likes and accepts it, it will also be added to their
        short term memory
        :param belief: Incoming belief(s) as Beliefs object
        :return True if accepted, else False
        """

        self._update_perceived_beliefs(belief)

        if self._is_belief_acceptable(belief):
            self._add_belief_to_memory(belief)
            self.belief_network.add_belief(belief)
            return True

        return False

    def is_conflicting_belief(self, belief):
        """
        Returns True is belief is of opposite valence as own belief.
        Returns False if belief is unknown or same sign of own valence
        :param belief: a Beliefs (one or more). If more than one belief is in
            Beliefs object, then any conflict returns True
        :return: True/False
        """

        for pair, valence in belief.items():
            if pair in self.belief_network:
                if BeliefModule.sign(self.belief_network.beliefs[pair]) \
                        != BeliefModule.sign(valence):
                    return True

        return False

    @staticmethod
    def sign(value):
        """
        :param value: a numeric
        :return: +1 if positive, -1 if negative
        """
        return (value > 0) - (value < 0)


def generate_random_belief_network_from_concepts(concept_sequence,
                                                 connection_probability,
                                                 valence_range=None,
                                                 rng=None):
    """
    Uses a sequence or set of concepts to generate a belief network in the
    same style as an erdos-renyi graph. Valences are drawn uniformly between
    the values of the valence_range.

    :param concept_sequence: a set or sequence of concepts
    :param connection_probability: value between [0,1], controls the density
        of the graph
    :param valence_range: the range between the lowest and highest valence.
        defaults to (-1, 1)
    :param rng: an instance of python Random. If none is given, an instance
        is generated with a seed determined by the default behavior of Random.
    :return: An instance of BeliefNetwork
    """

    if rng is None:
        # Generate default Random instance, it will be auto-seeded
        rng = Random()

    if valence_range is None:
        # Default range is (-1, 1)
        valence_range = (-1.0, 1.0)

    belief_net = BeliefNetwork()
    concept_sequence = list(concept_sequence)
    for i in range(len(concept_sequence)-1):
        for j in range(i+1, len(concept_sequence)):
            if rng.random() < connection_probability:
                belief_net.add_belief(belief=Beliefs({ConceptPair(concept_sequence[i],
                                                                  concept_sequence[j]):
                                                      rng.uniform(*valence_range)}),
                                      update_energy=False)

    return belief_net
