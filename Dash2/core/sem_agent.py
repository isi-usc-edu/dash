from Dash2.core.des_agent import DESAgent
from semopy import Model

class SEMAgent(DESAgent):
    """
    The Structural Equation Model (SEM) agent. This API defines the following methods:
    - agent_decision_cycle(self, **kwargs)
    """

    def __init__(self, **kwargs):
        DESAgent.__init__(self, **kwargs)
        self.model = None
        self.readSemModel(None) # actual model is passed in SEMAgent's sub-class
        self.trainModel(None)  # actual training data is passed in SEMAgent's sub-class

    ####################################################################################################################
    # This is agent's individual decision step.
    ####################################################################################################################
    def agent_decision_cycle(self, **kwargs):
        """
        Called when agent is activated.
        """
        agent_data = kwargs.get('agent_data', None) # pd dataframe
        if agent_data is None :
            raise AssertionError("decision_data_object and event_time cannot be None")

        # call prediction model and translate predictions to action
        preds = self.model.predict(agent_data)
        preds -= preds.mean()
        self.prediction_to_actions(preds)

        self.event_counter += 1
        return False

    ####################################################################################################################
    # Read semopy model
    ####################################################################################################################
    def readSemModel(self, mod):
        if mod is not None:
            self.model = Model(mod)

    ####################################################################################################################
    # Read semopy model
    ####################################################################################################################
    def trainModel(self, training_data):
        if training_data is not None:
            self.model.fit(training_data)

    ####################################################################################################################
    # Choose actions - implemented in subclasses
    ####################################################################################################################
    def prediction_to_actions(self, preds):
        return [] # should return list of callable actions