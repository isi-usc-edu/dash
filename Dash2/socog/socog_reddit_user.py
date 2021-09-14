"""
This is a short tutorial module that can be run with reddit_hub.
Reddit_hub contains a set of default comments on a soccer thread that
the user agent will parse and convert to beliefs, which it will then
assess. This uses System2 and System1 functions with the socog_module.

The user is instantiated with a sparse belief system where it believes that
Henry and the GreyTeam are the best. Initial forum posts validate this and
provide addition connections to the agent which reinforce its beliefs.

However, later comments suggest that Henry is Corrupt. After repeated
exposure the agent adopts beliefs the reject Henry and GreyTeams Best status
and adopt the beliefs that Henry and the GreyTeam are both Corrupt.
"""

from Dash2.socog.socog_module import *
from Dash2.socog.socog_dash_agent import SocogDASHAgent


class RedditMixin(object):
    """
    Test class for socog module
    """
    soccer = "Soccer"
    greyteam = "GreyTeam"
    henry = "Henry"
    best = "Best"
    corrupt = "Corrupt"
    concept_set = {soccer, greyteam, henry, best, corrupt}

    def __init__(self, **kwargs):
        self.server_host = kwargs.get("host", "localhost")
        self.server_port = kwargs.get("port", 5678)
        self.id = self.register()[1]

        self.readAgent(
            """
goalWeight BrowseReddit 1

goalRequirements BrowseReddit
    read_comment(Belief)
    process_belief(Belief)
    forget([read_comment(x), process_belief(x), sleep(x)])
            """)

        self.read_system1_rules(
            """
if last_comment(OtherBelief) and belief_conflict(OtherBelief) then emit_belief(OwnBelief) write_comment(OwnBelief)
if [Soccer,Corrupt,1.0] and [Soccer,Best,-1.0] then leave_thread()
            """)

        self.primitiveActions([
            ('read_comment', self.read_comment),
            ('write_comment', self.write_comment),
            ('last_comment', self.last_comment),
            ('leave_thread', self.leave_thread)])
        self.thread_location = 0
        self.my_comments = set()
        self.last_comment_belief = None
        self.intuit = True

    def _parse_comment(self, comment):
        """
        Constructs a belief from a comment
        :param comment: a string with two concepts and a supported relation
        :return: beliefs
        """

        first_concept = None
        second_concept = None
        for word in comment.split():
            if first_concept is None:
                if word in RedditMixin.concept_set:
                    first_concept = word
            else:
                if word in RedditMixin.concept_set:
                    second_concept = word

        if (first_concept is None) or (second_concept is None):
            raise NotImplementedError

        relation = comment.replace(first_concept, "")
        relation = relation.replace(second_concept, "")
        relation = relation.strip()

        if (relation == 'is') or (relation == 'is with'):
            valence = 1.0
        elif relation == 'is not':
            valence = -1.0
        else:
            raise NotImplementedError

        return Beliefs({ConceptPair(first_concept, second_concept): valence})

    def _construct_comment(self, belief):
        """
        Constructs a comment from a single belief
        :param belief: A Beliefs object with one element
        :return: A string that is the comment
        """
        concept_pair, valence = next(belief.iteritems())
        if valence > 0.0:
            association = " is "
        else:
            association = " is not "

        return concept_pair.concept1 + association + concept_pair.concept2

    def read_comment(self, goal_belief_tuple):
        goal = goal_belief_tuple[0]
        belief = goal_belief_tuple[1]
        status, comment = self.sendAction("read_comment", [self.thread_location])
        print(self.id, 'reading...', status, comment)
        # if no comment then it reached the end of the forum
        if comment:
            extracted_belief = self._parse_comment(comment)
            self.last_comment_belief = extracted_belief
            print(self.id, 'belief translation...', extracted_belief)
            # Move to next comment in thread and skip your own comments
            while True:
                self.thread_location += 1
                if self.thread_location not in self.my_comments:
                    break
            return [{belief: extracted_belief}]
        else:
            return [{}]

    def last_comment(self, goal_belief_tuple):
        goal = goal_belief_tuple[0]
        belief = goal_belief_tuple[1]

        if self.last_comment_belief is None:
            return []
        else:
            comment_belief = self.last_comment_belief
            self.last_comment_belief = None
            return [{belief: comment_belief}]

    def write_comment(self, goal_belief_tuple):
        goal = goal_belief_tuple[0]
        belief = goal_belief_tuple[1]

        comment = self._construct_comment(belief)
        print(self.id, "talking...", belief)
        status, comment_id = self.sendAction("write_comment", [comment])
        print(self.id, 'writing...', status, comment_id, comment)
        self.my_comments.add(comment_id)
        return [{}]

    def leave_thread(self, goal_belief_tuple):
        self.disconnect()


class RedditUser(RedditMixin, SocogDASHAgent):
    def __init__(self, **kwargs):
        SocogDASHAgent.__init__(self)
        RedditMixin.__init__(self, **kwargs)


if __name__ == '__main__':

    # Instantiate a belief module. It can start empty, but we will put in
    # a couple initial beliefs first. Note: Concepts need to be immutable
    # hashable types with __eq__ defined. A string will work.
    # The Concept class is also provided and it supports name/id values
    belief_module = BeliefModule(belief_net=BeliefNetwork(
        Beliefs({ConceptPair(RedditUser.soccer, RedditUser.greyteam): 1.0,
                 ConceptPair(RedditUser.greyteam, RedditUser.henry): 1.0,
                 ConceptPair(RedditUser.henry, RedditUser.best): 1.0,
                 ConceptPair(RedditUser.best, RedditUser.corrupt): -1.0,
                 ConceptPair(RedditUser.best, RedditUser.soccer): 1.0,
                 ConceptPair(RedditUser.henry, RedditUser.corrupt): -1.0}
                )), T=1.0, J=1.0, I=0.90, tau=1, recent_belief_chance=0.5,
        verbose=True, seed=2)

    RedditUser(port=6002, belief_module=belief_module).agent_loop(40)
