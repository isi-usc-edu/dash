# This class is inherited by the Dash class, transferring domain-independent human traits.
import random


class HumanTraits:
    def __init__(self, features='random'):
        self.genders = ['Male', 'Female']

        self.gender = 'undetermined'  # 'Male' or 'Female' or 'undetermined'

        # Big five characteristics. These are really categories but by default here can have a value of 0 to 1.
        self.extraversion = 0.5
        self.agreeableness = 0.5
        self.conscientiousness = 0.5
        self.emotional_stability = 0.5
        self.openness = 0.5

        # Might be found from the balloon assessment test for example.
        self.impulsivity = 0.5

        if features == 'random':  # set up a random person, useful for experiments, taken from phish_experiment_class
            self.choose_random_gender_personality()

    def choose_random_gender_personality(self, big_5_range=[0.2, 0.9]):
        genders = ['Male', 'Female']
        self.gender = random.choice(genders)
        self.extraversion = self.big_5_random(big_5_range)
        self.agreeableness = self.big_5_random(big_5_range)
        self.conscientiousness = self.big_5_random(big_5_range)
        self.emotional_stability = self.big_5_random(big_5_range)
        self.openness = self.big_5_random(big_5_range)

    def big_5_random(self, range):
        return random.uniform(range[0], range[1])

