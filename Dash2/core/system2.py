# Contains code relating to goal decomposition and mental model projection
from Dash2.core.string_aux import convert_camel
import ast
import time
import collections
import abc


class System2Agent:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.goalWeightDict = dict()
        self.goalRequirementsDict = dict()
        self.primitiveActionDict = dict()
        self.knownDict = dict()
        self.knownFalseDict = dict()
        self.transientDict = dict()
        self.transientDict['forget'] = [('forget', 'x')]  # Forget should be transient so you can keep forgetting things
        # Commenting out the line above will break something, but I need to be able to get past a 'forget'
        # clause in the middle of some goal requirements, which will never happen if forget is transient.
        # I think the best answer right now might be to add some judicious forget([forget(x)]) statements
        self.projectionRuleDict = dict()
        self.triggerRules = []
        self.utilityRules = []

        # Read the agent definition in a simpler syntax and create the appropriate definitions
        self.traceLoad = False
        self.traceParse = False
        self.traceKnown = False
        self.traceGoals = False
        self.traceClauses = False  # prints out information about clauses being tested for a goal
        self.traceForget = False
        self.traceProject = False

    def system2_propose_action(self):
        return self.choose_action_by_reasoning()

    def choose_action_by_reasoning(self):
        goal = self.chooseGoal()
        if goal is not None:
            return self.chooseActionForGoals([goal])
        else:
            if self.traceGoals:
                print('no unsatisfied goals')
            return None

    # A primitive action is declared in primitiveActionDict, or it might be a method
    # on the agent with the same name, or the same name with camelCase converted to underscores
    def isPrimitive(self, goal):
        predicate = goal[0]
        # Protect some predicates from being treated as primitive by this permissive method
        if predicate in ['known']:
            return False
        if predicate in self.primitiveActionDict:
            return True
        if hasattr(self, predicate) and callable(getattr(self, predicate)):
            return True
        underscore_action = convert_camel(predicate)
        if hasattr(self, underscore_action) and callable(getattr(self, underscore_action)):
            return True
        return False

    # Point to the internal structures of the other agent, typically to save space
    def use_system2(self, agent):
        self.goalWeightDict = agent.goalWeightDict
        self.goalRequirementsDict = agent.goalRequirementsDict
        self.primitiveActionDict = agent.primitiveActionDict
        #self.knownDict = agent.knownDict  # These are dynamic structures that should be separate for each agent
        #self.knownFalseDict = agent.knownFalseDict
        self.transientDict = agent.transientDict
        self.projectionRuleDict = agent.projectionRuleDict
        self.triggerRules = agent.triggerRules
        self.utilityRules = agent.utilityRules


    def readAgent(self, string):
        # state is used for multi-line statements like goalRequirements
        # and projection rules
        state = 0
        goalRequirements = 1
        project = 2
        utility = 3
        trigger = 4
        lines = []
        for line in string.split('\n'):
            if "#" in line:
                line = line[0:line.find("#")]
            line = line.strip()
            if state in [goalRequirements, project, utility, trigger]:
                if line == "":
                    if state == goalRequirements:
                        self.readGoalRequirements(lines)
                    elif state == project:
                        self.readProject(lines)
                    elif state == trigger:
                        self.readTrigger(lines)
                    elif state == utility:
                        self.readUtility(lines)
                    state = 0
                else:
                    lines.append(line)
            elif line.startswith("goalWeight"):
                self.readGoalWeight(line)
            elif line.startswith("goalRequirements"):
                state = goalRequirements
                lines = [line]
            elif line.startswith("known"):
                self.readKnown(line)
            elif line.startswith("primitive"):
                self.readPrimitive(line)
            elif line.startswith("project"):
                state = project
                lines = [line]
            elif line.startswith("trigger"):
                state = trigger
                lines = [line]
            elif line.startswith("utility"):
                state = utility
                lines = [line]
            elif line.startswith("transient"):
                self.readTransient(line)
            elif line != "":
                print("unrecognized line in readAgent:", line)

    def readGoalWeight(self, line):
        # line has form 'goalWeight predicate(arg1, arg2, ..) integer'
        goal = self.readGoalTuple(line[line.find(" "):line.rfind(" ")].strip())
        weight = int(line[line.rfind(" "):].strip())
        if self.traceLoad:
            print("Goal is ", goal)
        self.goalWeight(goal, weight)

    def readGoalRequirements(self, lines):
        goal = self.readGoalTuple(lines[0][lines[0].find(" "):].strip())
        requirements = [self.readGoalTuple(line) for line in lines[1:]]
        if self.traceLoad:
            print("Adding goal requirements for", goal, ":", requirements)
        self.goalRequirements(goal, requirements)

    def readKnown(self, line):
        goal = self.readGoalTuple(line[line.find(" "):].strip())
        self.knownTuple(goal)

    # Read a goal as a tuple from the line, which should start with the goal
    # description, e.g. goal(arg1, arg2, ..). Each arg may be a subgoal.
    # Uses the python compile's parser
    def readGoalTuple(self, line):
        # It's a compile module, with a statement node with one Discard object
        return self.parseToTuple(ast.parse(line).body[0].value)

    # It's tempting to leave the parse tree with the classes from the compile
    # module but I'd like to make it modular with abstraction
    def parseToTuple(self, parse):
        if isinstance(parse, ast.Name):
            return parse.id
        elif isinstance(parse, ast.Call):
            return tuple([self.parseToTuple(x) for x in [parse.func] + parse.args])
        elif isinstance(parse, ast.List):
            return [self.parseToTuple(x) for x in parse.elts]
        elif isinstance(parse, ast.BoolOp) and isinstance(parse.op, ast.And):
            return tuple(['and'] + [self.parseToTuple(x) for x in parse.values])
        elif isinstance(parse, ast.BoolOp) and isinstance(parse.op, ast.Or):
            return tuple(['or'] + [self.parseToTuple(x) for x in parse.values])
        elif isinstance(parse, ast.Constant):   # a string constant used
            if isinstance(parse.value, str):
                return "_" + parse.value
            else:
                return parse.value # old 2delete
        elif isinstance(parse, ast.Num):   # a number constant used
            return parse.n
        elif isinstance(parse, ast.Str):   # a number constant used
            return "_" + parse.s
        elif isinstance(parse, ast.UnaryOp) and isinstance(parse.op, ast.Not):
            return 'not', self.parseToTuple(parse.operand)
        else:
            print("Unhandled node type:", parse)
            raise BaseException

    @abc.abstractmethod
    def primitiveActions(self, line):
        """Implemented in DashAction"""
        return

    def readPrimitive(self, line):
        # 'primitive a, b, c' means that a, b and c and primitive actions with their own names as the defining functions
        self.primitiveActions(line[10:].split(", "))

    def readProject(self, lines):
        if self.traceParse:
            print("Reading projection rule from", lines)
        goal = self.readGoalTuple(lines[0][lines[0].find(" "):].strip())
        # Store a list of projection rules indexed by the goal
        head = goal
        if isinstance(goal, (list, tuple)):
            head = goal[0]
        if head not in self.projectionRuleDict:
            self.projectionRuleDict[head] = []
        effects = self.read_effect_lines(lines[1:])
        self.projectionRuleDict[head].append((goal, effects))

    def readTrigger(self, lines):
        if self.traceParse:
            print("Reading trigger rule from", lines)
        trigger = self.readGoalTuple(lines[0][lines[0].find(" "):].strip())
        effects = self.read_effect_lines(lines[1:])  # trigger effects are just like project rule effects
        self.triggerRules.append((trigger, effects))

    def read_effect_lines(self, lines):
        effects = []
        # To handle multi-line preconditions, group lines into a longLine that
        # contains a " + " or " - "
        longLine = ""
        for line in lines:
            longLine += line
            effectLine = longLine
            condition = True
            if "+ " in line or "- " in line:
                if "->" in longLine:
                    [precondLine, effectLine] = longLine.split("->")
                    condition = self.readGoalTuple(precondLine)
                effects.append(self.readEffectLine(effectLine, condition))
                longLine = ""
        return effects

    def readEffectLine(self, line, condition=True):
        line = line.lstrip(' ')
        p = ast.parse(line).body[0].value # old: ast.parse(line.strip()).node.nodes[0].expr
        if self.traceParse:
            print('Parse for effect line', line, 'is', p)
        # With no probabilities the results are UnaryAdd or UnaryDel, otherwise Add and Del,
        # Note the condition isn't included here
        if isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.UAdd): #isinstance(p, ast.UAdd):
            return Effect(Effect.add, self.parseToTuple(p.operand), condition, 1)
        elif isinstance(p, ast.UnaryOp) and isinstance(p.op, ast.USub): #isinstance(p, ast.USub):
            return Effect(Effect.delete, self.parseToTuple(p.operand), condition, 1)
        elif isinstance(p, ast.BinOp) and isinstance(p.op, ast.Add): #isinstance(p, ast.Add):
            if isinstance(p.left, ast.Name):
                return Effect(Effect.add, self.parseToTuple(p.right), condition, p.left.id)
            if isinstance(p.left, ast.Num):
                return Effect(Effect.add, self.parseToTuple(p.right), condition, p.left.n)
        elif isinstance(p, ast.BinOp) and isinstance(p.op, ast.Sub): #isinstance(p, ast.Sub):
            if isinstance(p.left, ast.Name):
                return Effect(Effect.delete, self.parseToTuple(p.right), condition, p.left.id)
            if isinstance(p.left, ast.Num):
                return Effect(Effect.add, self.parseToTuple(p.right), condition, p.left.n)
        else:
            print("No effects found", line)
            return None

    # Lines are of the form condition -> incr, and each match to condition increments
    # utility by that amount.
    def readUtility(self, lines):
        for line in lines[1:]:
            if self.traceProject:
                print("reading utility from", line)
            [precond, incr] = line.split("->")
            self.utilityRules.append([self.readGoalTuple(precond.strip()), float(incr)])
        if self.traceProject:
            print("Utility rules are", self.utilityRules)

    def readTransient(self, line):
        goal = self.readGoalTuple(line[line.find(" "):].strip())
        predicate = goal
        if isinstance(goal, (list,tuple)):
            predicate = goal[0]
        if predicate not in self.transientDict:
            self.transientDict[predicate] = []
        self.transientDict[predicate].append(goal)
        if self.traceLoad:
            print("Transient:", self.transientDict)

    def goalWeight(self, goal, weight):
        self.goalWeightDict[goal] = weight

    def goalRequirements(self, goal, requirements):
        # Treat as append, index by goal name (head)
        # and collate the goal itself with the body
        if goal[0] not in self.goalRequirementsDict:
            self.goalRequirementsDict[goal[0]] = []
        self.goalRequirementsDict[goal[0]].append((goal, requirements))

    def printGoals(self):
        for goal in self.goalWeightDict:
            print(goal, self.goalWeightDict[goal])

    def clearGoalsAndPlans(self):
        # Remove goals and plans, allowing new behaviors while leaving primitive actions
        self.goalWeightDict = {}
        self.goalRequirementsDict = {}
        self.projectionRuleDict = {}
        self.triggerRules = []
        self.utilityRules = []

    # Adds 'goal' as a known fact or completed goal
    def knownTuple(self, t):
        self.addTuple(t, self.knownDict)

    def knownFalseTuple(self, t):
        self.addTuple(t, self.knownFalseDict)

    def addTuple(self, t, adict):
        if t[0] not in adict:
            adict[t[0]] = []
        if t not in adict[t[0]]:
            if self.traceKnown:
                print("recording as known", t)
            adict[t[0]].append(t)

    def known(self, predicate, arguments=[]):
        self.knownTuple(tuple([predicate]) + tuple(arguments))  # this allows arguments to be any iterable

    def knownFalse(self, predicate, arguments):
        self.knownFalseTuple(tuple([predicate]) + tuple(arguments))

    # Might be subgoal or top-level goal
    def isGoal(self, goal):
        return goal[0] in self.goalRequirementsDict

    def chooseGoal(self):
        if self.goalWeightDict == {}:
            print('empty weight dict')
            return None
        # Return a goal with highest weight that is not already achieved (always returns the same one)
        validGoals = [item for item in self.goalWeightDict.items() if self.isKnown(item[0]) is False]
        if validGoals:
            return max(validGoals, key=lambda pair: pair[1])[0]
        else:
            return None

    def chooseActionForGoals(self, goals, indent=0):
        if goals is None:
            return None
        if self.traceGoals:
            print('  '*indent, "Seeking action for goals", goals)
        gpb = self.findGoalRequirements(goals[0])
        if gpb is []:
            print("No goal requirements match for ", goals[0])
            return None
        if self.traceClauses:
            print('  '*indent, "Requirements:", gpb)
        i = 1
        for (goal, requirements, bindings) in gpb:
            if self.traceClauses:
                print('  '*indent, '  ', 'trying req set', i, goal, requirements, bindings)
            # Return the first unfulfilled action in the requirements body, substituting bindings
            # but try the next requirements (if any) if there is a knownFalse subgoal in the requirements
            # 7/21/16 - wasn't substituting bindings so trying that (then moved back since didn't solve specific problem)
            na = self.nextAction(goal, requirements, bindings, indent)
            if na is not False and na is not None:
                # If the 'action' is the symbol 'known', then the main goal was achieved through
                # this goalRequirements clause. We need to compose the bindings so bindings for the 'local variables'
                # in the goal requirements clause propagate to those of the higher goal in the goal tree
                # and to any subsequent actions in its clause
                if na[0] == 'known':
                    composed = [(x, na[1][bindings[x]] if isinstance(bindings[x], str) and bindings[x] in na[1] else bindings[x])
                                for x in bindings]
                    uncomposed = [(x, na[1][x]) for x in na[1] if x not in bindings]
                    composed_bindings = dict(composed + uncomposed)
                    if self.traceClauses:
                        print('  '*indent, '  ', 'req set', i, 'succeeded with main bindings', bindings,
                            'and local bindings', na[1], 'and composed bindings', composed_bindings)
                    na[1] = composed_bindings
                return na
            i += 1
        return None

    # Recursively move through subgoals and return the next primitive action
    # To add: return False if a subgoal is knownFalse
    def nextAction(self, goal, requirements, bindings, indent):
        for candidate in requirements[1]:
            subbed = substitute(candidate, bindings)
            if self.traceGoals:
                print('  '*indent, "inspecting requirement", subbed, "from", candidate)
            known_bindings = self.isKnown(subbed)
            if known_bindings is not False:
                if self.traceGoals:
                    print('  '*indent, candidate, "subbed as", subbed, "and known with bindings", known_bindings)
                bindings = {**bindings, **known_bindings}  # wasteful but succinct
                if self.traceGoals:
                    print('  '*indent, "Bindings are now", bindings)
                continue
            elif self.isKnownFalse(subbed) is not False:  # a part of this goalset has been tried and failed in the past
                return None
            elif self.isPrimitive(subbed):
                if self.traceGoals:
                    print('  '*indent, "returning primitive", subbed)
                return subbed
            elif self.isGoal(subbed):
                action = self.chooseActionForGoals([subbed], indent + 2)
                if action is not None and action[0] == 'known':
                    # This subgoal was achievable from what is already done.
                    # Update bindings
                    old_bindings = bindings
                    bindings = {**bindings, **action[1]}
                    if self.traceGoals:
                        print('  '*indent, candidate, "already achieved")
                        print('  '*indent, "from subgoaling, old bindings were", old_bindings, "and now are", bindings)
                    continue
                else:
                    return action
            else:
                print('  '*indent, subbed, "is not a goal or primitive or already known")
                return None
        # If we got here, then we went through all the subactions without needing to do anything,
        # So the goal should be marked as achieved
        subbedGoal = substitute(goal,bindings)
        if not self.isTransient(subbedGoal):
            self.knownTuple(subbedGoal)
            if self.traceGoals:
                print("Marking", subbedGoal, "as achieved")
        return ['known', bindings]   # This return value lets the function know when subgoals are achieved vacuously

    # Known kind of conflates other ways of knowing things with knowing that a
    # subgoal has been performed
    def isKnown(self, goal):
        return self.isIn(goal, self.knownDict)

    def isKnownFalse(self, goal):
        return self.isIn(goal, self.knownFalseDict)

    def isTransient(self, goal):
        return self.isIn(goal, self.transientDict)

    # Need 'not' in there properly as well as deep variable replacement
    def notKnown(self, predicate):
        if self.isKnown(predicate):
            print("calling notknown with", predicate, ": false")
            return []
        else:
            print("calling notknown with", predicate, ": true")
            return [{}]

    # Create a list of all the known facts, used for projection
    # (Simple def used for functional abstraction)
    def knownList(self):
        return [fact if type(fact) is not tuple or len(fact) != 1 else fact[0] for goal in self.knownDict for fact in self.knownDict[goal]]

    def isIn(self, goal, adict):
        if goal[0] in adict:
            for term in adict[goal[0]]:
                bindings = unify(goal, term)
                if bindings is not False:  # Since {} means success with no new bindings
                    return bindings
        return False

    # This is a primitive built-in to remove all items matching a pattern from
    # knownDict and knowFalseDict
    def forget(self, action):
        forgotten = []
        for pattern in action[1]:
            if not isinstance(pattern, (tuple, list)):
                continue
            predicate = pattern[0]
            for d in [self.knownDict, self.knownFalseDict]:
                if predicate in d:
                    # not sure if I can modify the list I'm iterating across
                    to_remove = []
                    for fact in d[predicate]:
                        if unify(pattern, fact) is not False:
                            if self.traceForget:
                                print("Forgetting", fact)
                            to_remove.append(fact)
                    for fact in to_remove:
                        d[predicate].remove(fact)
                        forgotten.append(fact)
        return [{}]  # succeed as a primitive action, with no bindings

    def findGoalRequirements(self, goal):
        if goal[0] in self.goalRequirementsDict:
            # Return all possible bindings since we may be backtracking on them.
            # Later want to use an incrementally-built structure rather than a list.
            result = []
            for pair in self.goalRequirementsDict[goal[0]]:
                bindings = unify(goal, pair[0])
                if bindings != False:      # to include empty bindings
                    result.append((goal, pair, bindings))
            return result
        else:
            return []

    #################
    ## Projection
    #################

    def prefer_plan(self, plan_a, plan_b, initialWorld=None):
        if initialWorld == None:  # by default, start from what's known in the world
            initialWorld=self.knownList()
        if self.traceProject:
            print('initial world for a:')
            for fact in initialWorld:
                if self.my_size(fact) < 10:
                    print("  ", fact)
        exp_a = self.expectedUtility(self.project(plan_a, initialWorld))
        if self.traceProject:
            print('initial world for b:')
            for fact in initialWorld:
                if self.my_size(fact) < 10:
                    print("  ", fact)
        exp_b = self.expectedUtility(self.project(plan_b, initialWorld))
        # temporary
        if self.traceProject:
            print('a:', plan_a, exp_a, 'b:', plan_b, exp_b)
        return exp_a > exp_b

    # recursively count the elements in an s-expression
    def my_size(self, x):
        if type(x) in [list, tuple]:
            return sum([self.my_size(element) for element in x])
        else:
            return 1

    # If the first step in the plan is indicated, bind the step variable to it
    def prefer_first_step(self, goal_plan_step_var_tuple):
        goal = goal_plan_step_var_tuple[0]
        plan = goal_plan_step_var_tuple[1]
        step_var = goal_plan_step_var_tuple[2]
        if self.prefer_plan(plan, plan[1:]):
            if self.traceProject:
                print('True prefer first step projection with', goal, plan, step_var)
            return [{step_var: plan[0]}]
        else:
            if self.traceProject:
                print('False prefer first step projection with', goal, plan, step_var)
            return False

    def project(self, plan, state=[]):
        worlds = [state]
        for step in plan:
            new_worlds = []
            for world in worlds:
                new_worlds = new_worlds + self.project_step(step, world)
            worlds = new_worlds
        if self.traceProject:
            # Temporary
            print("Projecting", plan, "\n  yields", worlds)
        return worlds

    # Project a single step by finding the appropriate projection rule
    def project_step(self, step, world):
        if self.traceProject:
            print('projecting', step, 'on', world)
        head = step   # predicate for the rule, which is the step if it's a string..
        matched = False  # matched means a projection rule matched. Copied means we changed the world and copied it
        copied = False  # whether we have made a copy of the world to protect others from the same changes
        if isinstance(step, (list, tuple)):
            head = step[0]  #.. and otherwise the first element
        bindings = {}
        # Run the first matching projection rule
        if head in self.projectionRuleDict:
            rules = self.projectionRuleDict[head]
            for rule in rules:
                bindings = unify(rule[0], step) if isinstance(step, (list, tuple)) else {}  # why not all matches??
                if bindings is not False:
                    matched = True
                    if self.traceProject:
                        print("Rule", rule, "matches with bindings", bindings)
                    world, copied = self.apply_effects_list(rule[1], world, bindings, copied)
                    #return [world]  Now want to add triggers in the same function
                    break
        # Default effect if no rule matched
        if not matched:
            if self.traceProject:
                print('returning', [world + [('performed', step)]])
            if not copied:
                world = list(world)
                copied = True
            world = world + [('performed', step)]
        # Next run any triggers that match (will match them every step henceforth, but could add an effect to stop that)
        for trigger in self.triggerRules:
            all_bindings = allMatches(trigger[0], world, [bindings])
            for trigger_bindings in all_bindings:
                world, copied = self.apply_effects_list(trigger[1], world, trigger_bindings, copied)
        return [world]

    def apply_effects_list(self, effects, world, bindings, copied):
        for effect in effects:
            if effect.precondition is True or match_precond(substitute(effect.precondition, bindings), world):
                # As soon as we know there will be a change make sure this is a copy
                if not copied:
                    world = list(world)
                    copied = True  # but only need to copy once
                world = effect.update_world(world, bindings)
        return world, copied


    def utility(self, world):
        total = 0
        for rule in self.utilityRules:
            total += len(allMatches(rule[0], world)) * rule[1]
        #print('utility of', world, 'is', total)
        return total

    def expectedUtility(self, worlds):
        # Assume each world has the same weight and return the average utility
        return sum([self.utility(world) for world in worlds])/float(len(worlds))

    def sleep(self, action):
        print("Sleeping", action[1])
        time.sleep(action[1])
        return [{}]


def match_precond(precond, world):
    if precond is True:
        return True
    if isinstance(precond, (tuple, list)) and precond[0] == 'and':
        for sub_precond in precond[1:]:
            if not match_precond(sub_precond, world):
                return False
        return True
    elif isinstance(precond, (tuple, list)) and precond[0] == 'or':
        for sub_precond in precond[1:]:
            if match_precond(sub_precond, world):
                return True
        return False
    elif isinstance(precond, (tuple, list)) and precond[0] == 'not':
        if match_precond(precond[1], world):
            return False
        else:
            return True
    elif isinstance(precond, (tuple, str)):    # match a single goal
        return precond in world                       # trying to avoid python2-specific match
    else:
        return False


# Return a list of bindings list for all the ways a pattern can be matched
# in a world (list of facts). Not doing any fancy matching, so it's exponential.
# currentBindings defaults to one, empty, bindings list.
def allMatches(pattern, world, allBindings=[{}]):
    # Filter the world for the printout
    # Punting on 'and' and 'or' for now
    # For a term, extend each bindings list in every possible way
    if isinstance(pattern, (tuple, list)):
        matches = [b for b in [unify(fact, pattern, bindings) for fact in world for bindings in allBindings]
                   if b is not False]
        #print('all matches for', pattern, 'in', world, 'are', matches)
        return matches
    elif pattern in world:
        #print('one match for', pattern, 'in', world)
        return [{}]
    else:
        #print('no matches for', pattern, 'in', world)
        return []


# A probabilistic effect should really be a list of alternatives whose
# probability sum to 1 but for now I'm just providing a probability p,
# and we assume that the alternative is nothing happening with prob 1-p.
class Effect(object):

    add = 1
    delete = 0

    def __init__(self, addOrDelete, term, precondition=True, probability=1):
        self.addOrDelete = addOrDelete  # 1 means add, 0 means delete
        self.term = term  # thing being added or deleted
        self.precondition = precondition
        self.probability = probability

    def __repr__(self):
        return "<effect: %s -> %s %s>" % (self.precondition, '+' if self.addOrDelete == self.add else '-', self.term)

    # return a world after this effect happens in the input world (list of facts)
    def update_world(self, world, bindings):
        if isinstance(self.term, (list, tuple)):
            fact = substitute(self.term, bindings)
        else:
            fact = self.term
        if self.addOrDelete == Effect.add:
            if fact not in world:
                world.append(fact)   # surgically alters the list
        elif fact in world:
            world.remove(fact)
        return world


# Just clarifies the code a little
def isConstant(term):
    return not isVar(term)


def isVar(term):
    # Anything other than a string is assumed to be a constant
    # This test assumes python 2.x
    return isinstance(term, str) and not term.startswith("_")


# Substitute bindings in tuple representation of a term,
# where the first argument is the predicate.
# Needs to support structure in the term arguments.
def substitute(predicate, bindings):
    if isinstance(predicate, (list, tuple)):
        args = [substitute_argument(arg, bindings) for arg in predicate[1:]]
        return tuple([predicate[0]] + args)
    return substitute_argument(predicate, bindings)


def substitute_argument(arg, bindings):
    if isinstance(arg, list):
        return [substitute_argument(x, bindings) for x in arg]
    elif isinstance(arg, tuple):
        return tuple([substitute_argument(x, bindings) for x in arg])
    elif not isinstance(arg, collections.Hashable) or arg not in bindings:
        return arg
    else:
        return bindings[arg]

traceUnify = False

# Return bindings that would unify the pattern with the candidate, or False
def unify(pattern, candidate, bindings=None):
    if bindings is None:
        bindings = {}   # Cannot create dict in the argslist, or it's shared between every call
    if traceUnify:
        print("Trying unify", pattern, candidate, bindings)

    if isVar(pattern):
        if traceUnify:
            print("Pattern is variable:", pattern)
        if pattern == candidate:
            return bindings
        elif pattern in bindings and isConstant(bindings[pattern]):  # treat this as if it were the constant it's bound to. Don't bind vars to vars to avoid loops
            return unify(bindings[pattern], candidate, bindings)
        elif not isVar(candidate):
            if pattern in bindings: # bound to another variable. Bind them both to this constant
                bindings[bindings[pattern]] = candidate
            bindings[pattern] = candidate
            return bindings
        elif candidate in bindings:
            bindings[pattern] = bindings[candidate]
            return bindings
        else:
            bindings[pattern] = candidate
            return bindings
    elif isVar(candidate):   # candidate is a variable but pattern is not
        if traceUnify:
            print("Candidate", candidate, "is variable, not pattern", pattern)
        return unify(candidate, pattern, bindings)  # Use the case above
    elif isinstance(pattern, (list, tuple)):  # recursively match structures
        # Assume the first argument is a predicate name which has to be equal
        if isinstance(candidate, (list, tuple)) and len(pattern) == len(candidate) and (not pattern or pattern[0] == candidate[0]):
            if traceUnify:
                print("Pattern", pattern, "is a tuple, recursing")
            # Match the arguments in the goal and the requirements head
            for (goalarg, matcharg) in zip(pattern[1:], candidate[1:]):
                bindings = unify(goalarg, matcharg, bindings)
                if bindings is False:
                    return False
            return bindings
        else:
            if traceUnify:
                print("Pattern is a tuple but candidate is not, or has different predicate or length:", pattern, candidate)
            return False
    elif candidate != pattern:  # constants must match
        if traceUnify:
            print("Non-matching constants")
        return False
    elif candidate == pattern:
        if traceUnify:
            print("Same objects")
        return bindings
