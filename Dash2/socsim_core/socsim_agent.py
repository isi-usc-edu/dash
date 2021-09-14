import sys; sys.path.extend(['../../'])
from Dash2.socsim_core.output_event_log_utils import sort_data_and_prob_to_cumulative_array, random_pick_sorted
from Dash2.core.dash_agent import DASHAgent

AVG_MONTH_LENTH_SEC = (365.0/12.0)*24.0*3600.0

class ResourceEventTypePair(object):
    def __init__(self, event_index, res_id):
        self.event_index = event_index
        self.res_id = res_id


class SocsimDecisionData(object):

    platform_events_map = {}
    platform_events = []

    def __init__(self, **kwargs):
        """
        Initializes empty DecisionData object. If kwargs is empty object must be initialized via
        initialize_using_user_profile() after creation.
        :param kwargs: may contain such paramenters as id, event_rate, event_frequencies, login_h, etc.
        """
        # System 1 dynamic information needs to be separate for each agent. I will add general support for this later.
        self.nodes = set()
        self.action_nodes = set()
        # System 2 dynamic information needs to be separate for each agent. I will add general support for this later.
        self.knownDict = dict()
        self.knowFalseDict = dict()
        self.event_rate = kwargs.get("event_rate", 5)  # number of events per month
        self.id = kwargs.get("id", None)
        self.last_event_time = kwargs.get("event_rate", 0)


    def initialize_using_user_profile(self, profile, hub):
        """
        This method must be overridden/implemented in sub-classes.
        This method initializes SocsimUserDecisionData using information from initial state loader. Information from intial
        state loader is passes via profile object. Profile object is created and pickled by initial state loader.
        This method initializes:
            id, event_rate, last_event_time, etc.

        :param profile: contains information about the initial state of the agent, created by initial state loader.
        :param hub: hub is needed to register repos.
        :return: None
        """
        # id
        self.id = profile

        # hub
        self.hub = hub

        # the following attributes are copied from networkX graph object for performance optimization
        # however, it duplicated memory use for each attribute,
        # attributes can be accessed directly from the self.hub.graph.nodes[self.id]["attribute_name"]

        # resource event pairs
        self.event_res_pairs = []
        self.event_res_pairs_prob = []
        for res_id in hub.graph.neighbors(self.id):
            edge_data = hub.graph.get_edge_data(res_id, self.id)
            for event_index in self.platform_events_map.itervalues():
                if event_index in edge_data:
                    self.event_res_pairs.append(ResourceEventTypePair(event_index, res_id))
                    self.event_res_pairs_prob.append(edge_data[event_index])
        # normalize
        sum_ = sum(self.event_res_pairs_prob)
        self.event_res_pairs_prob = [float(v) / float(sum_) for v in self.event_res_pairs_prob]
        # rearrange in sorted lists
        self.event_res_pairs, self.event_res_pairs_prob = sort_data_and_prob_to_cumulative_array(self.event_res_pairs,
                                                                                                 self.event_res_pairs_prob)

       
class SocsimMixin(object):
    """
    A basic Git user agent that can communicate with a Git repository hub and
    perform basic actions. Can be inherited to perform other specific functions.
    """

    def _new_empty_decision_object(self):
        return SocsimDecisionData()

    def create_new_decision_object(self, profile):
        decisionObject = self._new_empty_decision_object()
        decisionObject.initialize_using_user_profile(profile, self.hub)
        return decisionObject

    def __init__(self, **kwargs):
        self.isSharedSocketEnabled = True  # if it is True, then common socket for all agents is used.
        # The first agent to use the socket, gets to set up the connection. All other agents with
        # isSharedSocketEnabled = True will reuse it.
        self.system2_proxy = kwargs.get("system2_proxy")
        if self.system2_proxy is None:
            self.readAgent(
                """
    goalWeight MakeEvent 1
    
    goalRequirements MakeEvent
      take_action()
                """)
        else:
            self.use_system2(self.system2_proxy)

        # Registration
        self.useInternalHub = kwargs.get("useInternalHub")
        self.hub = kwargs.get("hub")
        self.server_host = kwargs.get("host", "localhost")
        self.server_port = kwargs.get("port", 5678)
        self.trace_client = kwargs.get("trace_client", True)
        registration = self.register({"id": kwargs.get("id", None), "freqs": kwargs.get("freqs", {})})

        # Assigned information
        self.id = registration[1] if registration is not None else None

        self.traceLoop = kwargs.get("traceLoop", True)

        self.decision_data = None  # Should be set to the DecisionData representing the agent on each call

        # Actions
        self.primitiveActions([
            ('take_action', self.socsim_resource_event_pair_probabilistic_action)])

    def agent_decision_cycle(self):
        self.socsim_resource_event_pair_probabilistic_action()
        return False

    def socsim_resource_event_pair_probabilistic_action(self):
        """
        For demo purpose only.
        :return:
        """
        pair = random_pick_sorted(self.decision_data.event_res_pairs, self.decision_data.event_res_pairs_prob)
        selected_event = self.decision_data.platform_events[pair.event_index]
        selected_res = pair.res_id

        self.hub.log_event(self.decision_data.id, selected_res, selected_event, self.hub.time)

        print("Primitive resource-repo pair action taken.")

    def first_event_time(self, start_time, max_time):
        """
        Return time of the first event in the given interval. Result is either between start_time and max_time or None.
        None is returned when agent does not take actions in the given time interval.
        :param start_time:
        :param max_time:
        :return:
        """
        delta = AVG_MONTH_LENTH_SEC / float(self.hub.graph.nodes[self.decision_data.id]["r"])
        next_event_time = self.hub.graph.nodes[self.decision_data.id]["let"] + delta if self.hub.graph.nodes[self.decision_data.id]["let"] is not None \
            and self.hub.graph.nodes[self.decision_data.id]["let"] != -1 else start_time
        while next_event_time < start_time:
            next_event_time += delta
        if max_time >= next_event_time >= start_time:# and next_event_time <= max_time:
            return next_event_time
        else:
            return None

    def next_event_time(self, curr_time, start_time, max_time):
        delta = AVG_MONTH_LENTH_SEC / float(self.hub.graph.nodes[self.decision_data.id]["r"])
        next_time = curr_time + delta
        if max_time >= next_time >= start_time:# and next_time <= max_time:
            return next_time
        else:
            return None

class SocsimAgent(SocsimMixin, DASHAgent):
    def __init__(self, **kwargs):
        DASHAgent.__init__(self)
        SocsimMixin.__init__(self, **kwargs)
