from Dash2.core.dash_agent import DASHAgent
import random
import math

class TimedTestAgent(DASHAgent):

    time = 0
    eat_state = 0

    def __init__(self):
        DASHAgent.__init__(self)

#        self.traceGoals = True
        self.register()

        self.readAgent("""

goalWeight doWork 1

goalRequirements doWork
    wakeUp(placeholder)
    run(placeholder)
    eat(_breakfast)
    eat(_lunch)
    eat(_dinner)
    sleep(placeholder)
    forget([wakeUp(x), run(x), eat(x), sleep(x)])

transient doWork
    """)

        self.primitiveActions([
                ('wakeUp', self.wake_up),
                ('run', self.run),
                ('eat', self.eat),
                ('sleep', self.sleep)
                ])

    def wake_up(self, goal_ph_tuple):
        (goal, ph) = goal_ph_tuple
        wake_up_time = 24 * math.floor((self.time+2)/24) + 6
        print("woke up...")
        self.sendAction(goal, [], wake_up_time)
        self.time = wake_up_time
        return [{}]

    def run(self, goal_ph_tuple):
        (goal, ph) = goal_ph_tuple
        run_time = 24 * math.floor(self.time/24) + 7
        print("running...")
        self.sendAction(goal, [], run_time)
        self.time = run_time
        return [{}]

    def eat(self, goal_meal_var_tuple):
        (goal, meal_var) = goal_meal_var_tuple
        if self.eat_state == 0:
            curr_meal = "breakfast"
            self.eat_state = 1
            eat_time = 24 * math.floor(self.time/24) + random.randint(8,9)
        elif self.eat_state == 1:
            curr_meal = "lunch"
            self.eat_state = 2
            eat_time = 24 * math.floor(self.time/24) + random.randint(11,14)
        elif self.eat_state == 2:
            curr_meal = "dinner"
            self.eat_state = 0
            eat_time = 24 * math.floor(self.time/24) + random.randint(18, 20)
        else:
            print("eat primitive action: shouldn't be here...")
            return []

        print("eating...", goal, meal_var)
        self.sendAction(goal + "(" + meal_var + ")", [], eat_time)
        self.time = eat_time
        return [{}]
#        return [{meal_var: curr_meal}]

    def sleep(self, goal_ph_tuple):
        (goal, ph) = goal_ph_tuple
        sleep_time = 24 * math.floor(self.time/24) + 22
        print("sleeping...")
        self.sendAction(goal, [], sleep_time)
        self.time = sleep_time
        return [{}]

if __name__ == '__main__':
    TimedTestAgent().agent_loop(20)
