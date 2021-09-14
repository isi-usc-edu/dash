
# A measure is a function of the agent state, possibly over a period of time or of a set of agents,
# that is used as a measure of the agent system performance.
# A measure can be associated either with an agent definition or an experiment, and can be added dynamically.
# There is an associated function to compute the measure.

# 'target' and 'backing' are currently in flux but are meant to represent a target value and experimental backing
# for the target value respectively. They should probably be grouped in an object so we can have multiple values
# and backings with conditions on them, e.g. the forgetting rate is X for teens, Y for elders in Singapore per paper P


class Measure:

    def __init__(self, name, function=None, target=None, backing=None):
        self.name = name
        self.function = self.name if function is None else function
        self.target = target
        self.backing = backing

    def __repr__(self):
        return "M: " + str(self.name)

    # Evaluate the measure on an object for which it is defined, e.g. an agent or experiment.
    def eval(self, measure_object):
        # If the function slot is a string, find it as a method on the object and call it.
        if isinstance(self.function, str):
            if getattr(measure_object, self.function) and callable(getattr(measure_object, self.function)):
                return getattr(measure_object, self.function)()


# A constraint in this context is a constraint on the outcome of an experiment, so in simple form it names a measure
# and target values for the measure.
class Constraint:

    def __init__(self, measure, target):
        self.measure = measure
        self.target = target
