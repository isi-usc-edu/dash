import random
import numbers
import scipy.stats


# A parameter represents a variable for an agent that the FARM system can investigate.
# The list of parameters is declared with the agent definition, e.g. mailReader.py. When an agent is instantiated,
# the parameter name is set as an attribute of the agent, with the parameter default value or with a value
# drawn from the distribution declared for the parameter.
class Parameter:

    def __init__(self, name, distribution=None, default=None, value_set=None, range=None, source=None):
        self.name = name
        self.distribution = distribution
        self.default = default
        self.value_set = value_set  # value_set may be a list or a range such as Range(0,1) (assumed to be closed)
        if value_set is None and range is not None:
            self.value_set = Range(range[0], range[1])
        self.source = source

    def __repr__(self):
        string = "P[" + self.name + ", " + \
                 (str(self.distribution) if self.distribution is not None else str(self.value_set))
        if self.default is not None:
            string += ", " + str(self.default)
        if self.source is not None:
            string += " (source=", str(self.source) + ")"
        return string + "]"


class Boolean(Parameter):

    def __init__(self, name, distribution=None, default=None):
        Parameter.__init__(self, name, distribution, default, value_set=[True, False])

        # If the distribution is not filled if, default to equal chance True and False
        if distribution is None:
            self.distribution = Equiprobable(self.value_set)


# A continuous closed range of numbers
class Range:

    def __init__(self, min_val, max_val, step=1):
        self.min = min_val
        self.max = max_val
        self.step = step

    def __repr__(self):
        return "Range(" + str(self.min) + ", " + str(self.max) + ", " + str(self.step) + ")"


# General class of distributions for parameters
class Distribution:

    def __init__(self):
        parameter = None  # A pointer to the parameter if useful, e.g. to get the value set
        pass

    def __repr__(self):
        return "Null distribution"

    # Returns a value randomly drawn from the distribution
    def sample(self):
        pass

    def mean(self):
        pass


class Uniform(Distribution):

    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __repr__(self):
        return "Uniform(" + str(self.min_value) + ", " + str(self.max_value) + ")"

    def sample(self):
        return random.uniform(self.min_value, self.max_value)

    def mean(self):
        return (self.max_value - self.min_value)/2.0


# Identical to above, but will only return an integer between min_value and max_value, which should be integers
# included in the range.
class IntegerUniform(Distribution):

    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    def __repr__(self):
        return "Integer uniform(" + str(self.min_value) + ", " + str(self.max_value) + ")"

    def sample(self):
        return random.randrange(self.min_value, self.max_value + 1)

    def mean(self):
        return (self.max_value - self.min_value)/2.0  # mean need not be an integer


# This class currently assumes an immutable finite set of possible values, so the mean is precomputed if applicable.
class Equiprobable(Distribution):

    def __init__(self, values):
        self.values = values
        # Check this at build time so it is just done once
        self.numeric = all(isinstance(x, numbers.Number) for x in self.values)
        # May as well pre-compute the mean too
        self.mean = sum(self.values)/float(len(self.values)) if self.numeric else None

    def __repr__(self):
        return "Equiprobable(" + str(self.values) + ")"

    def sample(self):
        return random.choice(self.values)

    # mean is defined if all the values are numbers. Don't want to test that every time
    def mean(self):
        return self.mean


class Normal(Distribution):

    def __init__(self, mean, variance):
        self.mean = mean
        self.variance = variance

    def __repr__(self):
        return "Normal(" + str(self.mean) + "," + str(self.variance) + ")"

    def sample(self):
        return random.gauss(self.mean, self.variance)

    def mean(self):
        return self.mean

    def variance(self):
        return self.variance


# Truncated normal, i.e. normal distribution but with fixed min and max. I'm using this
# for distributions of probabilities, with min 0 and max 1.
class TruncNorm(Distribution):

    def __init__(self, orig_mean, orig_std, mymin, mymax):
        self.min = mymin
        self.max = mymax
        self.orig_mean = orig_mean  # mean of the underlying normal distribution
        self.orig_std = orig_std  # variance of the underlying normal distribution
        # truncnorm always has mean 0 variance 1 so adjust min and max, then re-adjust on sampling.
        self.rv = scipy.stats.truncnorm((self.min - self.orig_mean)/float(self.orig_std),
                                        (self.max - self.orig_mean)/float(self.orig_std))

    def __repr__(self):
        return "Truncated Normal(" + str(self.orig_mean) + ", " + str(self.orig_std) + ") [" + str(self.min) \
            + ", " + str(self.max) + "]"

    def sample(self):
        return self.rv.rvs() * self.orig_std + self.orig_mean

