import sys
sys.path.extend(['../../']) # need to have 'webdash' directory in $PYTHONPATH, if we want to run script (as "__main__")
from Dash2.core.sem_agent import SEMAgent
from semopy import Model
from semopy.examples import political_democracy
desc = political_democracy.get_model()
data = political_democracy.get_data()

class NaiveSEMAgent(SEMAgent):
    """
    NaiveSEMAgent - example from https://semopy.com/predict.html
    """

    def __init__(self, **kwargs):
        SEMAgent.__init__(self)
        self.readSemModel(""" 
# measurement model
ind60 =~ x1 + x2 + x3
dem60 =~ y1 + y2 + y3 + y4
dem65 =~ y5 + y6 + y7 + y8
# regressions
dem60 ~ ind60
dem65 ~ ind60 + dem60
# residual correlations
y1 ~~ y5
y2 ~~ y4 + y6
y3 ~~ y7
y4 ~~ y8
y6 ~~ y8
                        """) # prediction model
        self.readSemModel(desc) # just to test
        training_data = data # initial training data
        self.trainModel(training_data)

    def prediction_to_actions(self, preds):
        #TODO: convert [dem60, dem65, ind60] predictions into action(s)
        return [] # should return list of callable actions



if __name__ == "__main__":
    NaiveSEMAgent().agent_loop()
