from Dash2.socog.socog_module import BeliefModule
from Dash2.socog.socog_module import ConceptPair


class SocogSystem1Agent(object):
    """
    A system1 class that uses a belief module and system rules to fill
    a queue of actions that the agent will attempt to take.

    It cannot be instantiated on its own. It must be inherited by a DASH agent
    """

    boolean_token = {'and', 'or', 'not', 'true', 'false'}
    boolean_non_operands = {'and', 'or', 'not', '(', ')'}
    binary_operators = {'and', 'or'}
    
    def __init__(self, belief_module=None):
        """
        :param belief_module: A BeliefModule object

        :properties:
        rule_list: is a list of tuples where the first element is the condition,
            and the second a sequence of actions.
        belief_token_map: a dictionary keyed by belief string and valued by
            the corresponding token (a concept_pair, valence tuple)
        action_token_map: a dictionary keyed by an action string and valued
            by a tuple who's first element is action name and following elements
            the variable names
        action_name_to_variable_map: a dictionary keyed by action name and valued
            by a list of variables that primitive has
        variable_bindings: a dictionary keyed by variable name and valued by
            the value of that variable (defaults to None)
        action_queue: a list of action strings to be carried out.
        current_action: a pointer to an action in the action_queue
        """

        if belief_module is None:
            self.belief_module = BeliefModule()
        else:
            self.belief_module = belief_module

        # A list of tuples. The first element is the condition, the second a
        # sequence of actions.
        self.rule_list = []
        self.belief_token_map = {}
        self.action_token_map = {}
        self.action_name_to_variable_map = {}
        self.variable_bindings = {}
        self.action_queue = []
        self.current_action = 0  # points to action in queue
        self._recursion_flag = False

    def read_system1_rules(self, rule_string):
        """
        Adds rules from the given string into the list of rules in the socog
        system1.

        :param rule_string: A string containing lines for each system rule.
            A system rule is defined by a condition and sequence of actions.
            If the condition is fulfilled, the sequence is carried out. The
            condition is a logical statement that can use and, or, not, and
            parentheses. The action statement is a sequence of primitive actions
            separated by spaces. The conditions must specify beliefs, which
            require three values to be specified: two concepts and a valence.
            E.g:
                if [A,B,0.5] and [C,B,-0.2] then run(speed) jump(height)

            Actions can also be added to conditions:

                if foo(Belief) and fee(Belief,height) then jump(height)
                if foo(Belief) and [A,B,1.0] then run(speed)

            Square brackets are used to designate a belief. Each concept and
            the valence are separated by ','.

            Note: setting valence to 0.0 is ambiguous and will return True if
                the agent has the belief.

            Note: The 'True' word can be used to designate conditions that will
                always return true, e.g.:
                    if [True] then talk(belief) call(belief)
                    if [false] or not [TRUE] then talk(belief) call(belief)

            Note: precedence is from left to right or determined by parenthesis

            Note: Syntax is case sensitive, except for logical operators as
                beliefs themselves are case-sensitive

        :return: None
        """
        # Parse string into sub-strings for each rule
        for rule in rule_string.splitlines():
            if 'if' == rule.strip()[0:2]:
                self.rule_list.append(SocogSystem1Agent.parse_rule(rule))

        self.belief_token_map.update(self._construct_belief_token_map(self.rule_list))
        self.action_token_map.update(self._construct_action_token_map(self.rule_list))
        self.action_name_to_variable_map.update(
            self._construct_action_name_to_variable_map(self.action_token_map))
        self.variable_bindings.update(self._construct_variable_binding_map(
            self.action_token_map))

    def _swap_token_variables(self, split_belief_token):
        """
        Swaps variable location and builds a new string with concept locations
        swapped.
        :param split_belief_token: a belief token that has been split into its
            elements
        :return: a string representing the same token but with variable locations
            swapped.
        """

        return split_belief_token[1] + "," + split_belief_token[0] \
               + "," + split_belief_token[2]

    def _construct_belief_token_map(self, rule_list):
        """
        Creates concept_pair, valence tuple from belief tokens
        :param rule_list: a tokenized list of rules
        :return: dictionary keyed by belief token and valued by a tuple:
            (concept_pair, valence)
        """

        belief_token_map = {}
        for rule in rule_list:
            for token in rule[0]:
                self.add_belief_token_to_map(token, belief_token_map)

        return belief_token_map

    def _construct_action_token_map(self, rule_list):
        """
        Creates action tuple in format used by DASH
        :param rule_list: a tokenized list of rules
        :return: dictionary keyed by action token and valued by a tuple
        """

        action_token_map = {}
        for rule in rule_list:
            # Add actions from condition
            for token in rule[0]:
                if SocogSystem1Agent.is_action_token(token):
                    self.add_action_token_to_map(token, action_token_map)
            
            # Add actions from action sequence
            for token in rule[1]:
                self.add_action_token_to_map(token, action_token_map)

        return action_token_map

    def _construct_action_name_to_variable_map(self, action_token_map):
        """
        Creates a map from action names to a list of variables.
        The map is used for determining which bindings go to which variables
        for which functions.

        :param action_token_map: keyed by action valued by token -> tuple
            with first element the action name and following elements the
            variable names.
        :return: dictionary keyed by action name and valued by variable list
        """

        action_variable_map = {}
        for action_tuple in action_token_map.values():
            action_variable_map[action_tuple[0]] = list(action_tuple[1:])

        return action_variable_map

    def _construct_variable_binding_map(self, action_token_map):
        """
        Creates variable to value map. Defaults all values to None.
        These values are only updated to an actual value when bound.
        Note: If the mapping is None, then the variable string is used,
            which DASH will use to set the variable

        :param action_token_map: keyed by action valued by token -> tuple
            with first element the action name and following elements the
            variable names.
        :return: dictionary keyed by variable name and valued by variable value
            if it has one.
        """

        variable_value_map = {}
        for action_tuple in action_token_map.values():
            for variable in action_tuple[1:]:
                variable_value_map[variable] = None

        return variable_value_map

    def add_action_token_to_map(self, token, token_map):
        """
        Checks if token is valid, and if so, adds it to the map in-place
        :param token: a action token
        :return: same reference to map
        """

        if SocogSystem1Agent.is_action_token(token):
            action_name, arguments = token[:-1].split('(')
            arguments = arguments.replace(' ', '').split(',')
            token_map[token] = tuple([action_name] + arguments)

        return token_map

    def add_belief_token_to_map(self, token, token_map):
        """
        Checks if token is valid, and if so, adds it to the map in-place
        :param token: a condition token
        :return: same reference to map
        """
        if SocogSystem1Agent.is_belief_token(token):
            split_token = token.split(",")
            concept_pair = ConceptPair(split_token[0], split_token[1])
            token_map[token] = (concept_pair, float(split_token[2]))
            # To keep variable order invariant have to swap variables
            doppelganger_token = self._swap_token_variables(split_token)
            token_map[doppelganger_token] = (concept_pair,
                                             float(split_token[2]))

        return token_map

    @staticmethod
    def parse_string_to_tokens(condition_string):
        """
        Splits the condition string into a list of tokens, e.g. terminals
        and operators and parentheses and actions.
        :param condition_string: a string representation of the condition
        :return: token list
        """
        slice_start = Index(0)
        slice_end = Index(1)
        tokens = []
        while slice_start.pos < len(condition_string):
            if condition_string[slice_start.pos].isalnum() \
                    or condition_string[slice_start.pos] == '[':
                tokens.append(SocogSystem1Agent.parse_token_expression(
                    condition_string, slice_start, slice_end))
                slice_start.pos = slice_end.pos

            elif condition_string[slice_start.pos] == ')':
                tokens.append(')')

            elif condition_string[slice_start.pos] == '(':
                tokens.append('(')

            elif condition_string[slice_start.pos] == ']':
                raise ValueError("Error: unexpected closing bracket ]")

            slice_start.increment()
            slice_end.pos = slice_start.pos + 1

        return tokens

    @staticmethod
    def parse_token_expression(condition_string, slice_start, slice_end):
        """
        Parses either an action or belief token from a string
        :param condition_string: a string matching the syntax requirements of
            a condition_string - see read_system1_rules
        :param slice_start: start Index
        :param slice_end: end Index
        :return: parsed token
        """
        if condition_string[slice_start.pos] == '[':
            slice_start.increment()
            while condition_string[slice_end.pos] != ']':
                slice_end.increment()

        elif condition_string[slice_start.pos].isalnum():
            while slice_end.pos < len(condition_string):

                if (condition_string[slice_start.pos:slice_end.pos].lower()
                    in SocogSystem1Agent.boolean_token) \
                       and condition_string[slice_end.pos] == ' ':
                    break

                if condition_string[slice_end.pos] == '(':
                    while condition_string[slice_end.pos] != ')':
                        slice_end.increment()
                    slice_end.increment()
                    break

                slice_end.increment()

        return condition_string[slice_start.pos:slice_end.pos].replace(' ','')

    @staticmethod
    def parse_action_expression(action_string):
        """
        :param action_string: string representing the action
        :return: a tuple of the form ('function_name', (variables))
        """

        return action_string

    @staticmethod
    def parse_rule(rule):
        """
        Splits a single rule, represented as a string, into a condition string
        and an action string.
        :param rule: a single if/then string
        :return: tuple (condition string, action string)
        """

        # Strip everything unnecessary for condition and action parsing
        condition, action = rule.split("then")
        condition = condition.strip()
        condition = condition.replace("if", "", 1)
        action = action.strip().split(" ")

        return SocogSystem1Agent.parse_string_to_tokens(condition), \
               SocogSystem1Agent.parse_action_expression(action)

    def is_belief_condition_satisfied(self, concept_pair, valence):
        """
        Checks if the condition is satisfied in the belief system
        :param concept_pair
        :param valence
        :return: boolean
        """
        if concept_pair in self.belief_module.belief_network:
            belief_valence = self.belief_module.belief_network.beliefs[concept_pair]
            if (valence > 0) and (belief_valence > valence):
                return True
            elif (valence < 0) and (belief_valence < valence):
                return True

        return False

    @staticmethod
    def is_operand_token(token):
        """
        :param token: a tokenized string
        :return: boolean
        """

        return token.lower() not in SocogSystem1Agent.boolean_non_operands
    
    @staticmethod
    def is_binary_operator_token(token):
        """
        :param token: a tokenized string
        :return: boolean
        """

        return token.lower() in SocogSystem1Agent.binary_operators
    
    @staticmethod
    def is_belief_token(token):
        """
        :param token: a tokenized string
        :return: boolean
        """

        return token.count(',') == 2
    
    @staticmethod
    def is_action_token(token):
        """
        :param token: a tokenized string
        :return: boolean
        """

        return ('(' in token) and (')' in token)
    
    @staticmethod
    def valid_operator_token(tokens, index):
        """
        Returns True if the token at index.pos exists and is an operator
        :param tokens: a list of tokens
        :param index: Index object
        :return: boolean
        """

        if index.pos >= len(tokens):
            return False

        return SocogSystem1Agent.is_binary_operator_token(tokens[index.pos])
    
    def _is_belief_token_satisfied(self, belief_token):
        """
        :param belief_token: string representing a belief
        :return: True/False
        """

        if belief_token in self.belief_token_map:
            return self.is_belief_condition_satisfied(
                *self.belief_token_map[belief_token])

        elif SocogSystem1Agent.is_belief_token(belief_token):
            self.add_belief_token_to_map(belief_token, self.belief_token_map)
            return self._is_belief_token_satisfied(belief_token)

        else:
            raise ValueError("Error: Invalid token input <" +
                             belief_token + "> does not have a truth value")
        
    def parse_expression(self, tokens, index=None):
        """
        A boolean logic parser that is implemented as a recursive decent parser.
        :param tokens: list of tokens
        :param index: index location in tokens (default 0)
        :return: boolean value
        """

        if index is None:
            index = Index()

        while index.pos < len(tokens):
            is_negated = False
            if tokens[index.pos].lower() == 'not':
                is_negated = True
                index.increment()

            evaluation = self.parse_subexpression(tokens, index)
            if is_negated:
                evaluation = not evaluation

            while SocogSystem1Agent.valid_operator_token(tokens, index):
                operator = tokens[index.pos].lower()
                index.increment()
                if index.pos >= len(tokens):
                    raise IndexError("Error: Missing expression after operator: "
                                     + str(tokens[index.pos - 1]) + " at "
                                     + str(index.pos))

                next_evaluation = self.parse_subexpression(tokens, index)
                if operator == 'and':
                    evaluation = evaluation and next_evaluation
                elif operator == 'or':
                    evaluation = evaluation or next_evaluation
                else:
                    raise AssertionError("Error: Unknown operator")

            return evaluation

        raise IndexError("Empty expression")
    
    def parse_subexpression(self, tokens, index=None):
        """
        Parses subexpressions. Is a part of the parse_expression function.
        :param tokens: list of tokens
        :param index: index location in tokens (default 0)
        :return: boolean value
        """
        if index is None:
            index = Index()

        if SocogSystem1Agent.is_belief_token(tokens[index.pos]):
            token_evaluation = self._is_belief_token_satisfied(tokens[index.pos])
            index.increment()
            return token_evaluation

        if SocogSystem1Agent.is_action_token(tokens[index.pos]):
            # Recursion flag is to prevent actions from
            # resetting the stack and condition check indefinitely
            self._recursion_flag = True
            token_evaluation = self.evaluate_action(self.action_token_map[
                                                        tokens[index.pos]])
            self._recursion_flag = False
            index.increment()
            return bool(token_evaluation)

        elif tokens[index.pos].lower() == 'true':
            index.increment()
            return True

        elif tokens[index.pos].lower() == 'false':
            index.increment()
            return False

        elif tokens[index.pos] == '(':
            index.increment()
            expression_eval = self.parse_expression(tokens, index)
            if tokens[index.pos] != ')':
                raise IndexError("Error: Expected closed parenthesis")

            index.increment()
            return expression_eval

        elif tokens[index.pos] == ')':
            raise IndexError("Error: Unexpected closed parenthesis")

        else:
            return self.parse_expression(tokens, index)
    
    def is_condition_satisfied(self, condition):
        """
        Parses the condition tokens and evaluates whether they are satisfied
        or not.
        :param condition: a tokenized list from the rule_list
        :return: boolean
        """
        return self.parse_expression(condition)
    
    def actions_from_satisfied_conditions(self):
        """
        Check all conditions in rule_list and return a list of actions
        that satisfy those conditions
        :return: A list of iterable things that have a node_to_action method
        """

        active_actions = []
        for condition, actions in self.rule_list:
            if self.is_condition_satisfied(condition):
                for action in actions:
                    active_actions.append(self.action_token_map[action])

        return active_actions
    
    def evaluate_action(self, action):
        """
        Calls on the Socog agent to perform a given action and returns the
        result
        :param action: a DASH formatted action 
        :return: output of the primitive action
        """
        result = self.performAction(
            self.bind_variables_if_available(action))
        self.update_beliefs(result, action)
        return result
    
    def initialize_action_queue(self):
        """
        Fills system1's action queue with actions found to satisfy the
        conditions of its rules.

        Uses a recursion flag to prevent actions that are called from the
        condition check to call another condition check.

        :return: None
        """
        if not self._recursion_flag:
            actions = self.actions_from_satisfied_conditions()
            self.reset_action_queue(actions)
            
    def system1_update(self, result=None):
        """
        Checks conditions and taken actions. Increments to the next action
        if one is performed. Resets if it fails. Resets if conditions change.
        :param result: the result of the chosen action
        :return: None
        """

        # If system 1 was not chosen, and we are at the start, reset
        # If system 1 action was taken but it failed, reset
        # If system 1 action queue is complete, reset
        if (self.current_action == 0 and
            not self.sys1_action_taken) or \
                (self.sys1_action_taken and not bool(result)) or \
                (self.current_action == (len(self.action_queue) - 1)):
            self.initialize_action_queue()

        # If system 1 action taken and it was successful move to next action
        if self.sys1_action_taken and bool(result):
            self.update_action_queue()

        # If system 1 action was not taken and we aren't on the first action
        # then nothing happens and it waits until it can perform the rest
        # of the actions in the sequence

        # note: it can be reset externally via process_belief

        # Resets the SocogDASHAction variable for tracking whether an action is
        # taken
        self.sys1_action_taken = False

    def select_action_from_queue(self):
        """
        Selects an action at the front of the queue (determined by current_action).

        It checks variable bindings and substitutes the arguments
        with binding values if present, else the arguments remain as the
        given strings.

        When queue is complete, it resets bindings and starts at the beginning

        :return: DASH formatted action (or None)
        """

        if self.current_action < len(self.action_queue):
            action = self.action_queue[self.current_action]
            return self.bind_variables_if_available(action)

        elif len(self.action_queue) == 0:
            return None

        else:
            self.update_action_queue()
            return self.select_action_from_queue()

    def system1_propose_action(self):
        """
        Part of the system1 API. Calls select_action_from_queue.
        :return: action
        """
        return self.select_action_from_queue()

    def system1_step(self):
        """
        Does nothing atm. Part of System1 API
        """
        pass

    def update_action_queue(self):
        """
        Increments the current_action pointer
        :return: None
        """

        if self.current_action < len(self.action_queue):
            self.current_action += 1

        # Reset queue and bindings
        else:
            self.current_action = 0
            self.clear_variable_bindings()

    def reset_action_queue(self, action_list):
        """
        Empties queue, and calculates what conditions are satisfied and adds
        them to the queue. Also clears all variable bindings
        :return: None
        """
        self.action_queue = []
        self.current_action = 0
        self.clear_variable_bindings()
        self.add_actions_to_queue(action_list)

    def clear_variable_bindings(self):
        """
        Sets all binding values in variable bindings to None
        :return: None
        """

        for key in self.variable_bindings.keys():
            self.variable_bindings[key] = None

    def add_actions_to_queue(self, action_list):
        """
        Adds actions to the right of the action queue
        :param action_list: a list of primitive actions
        :return: None
        """
        self.action_queue += action_list

    def bind_variables_if_available(self, action):
        """
        Will go through each variable in the action and bind it if bindings
        exist.
        :param action: an action tuple
        :return: action tuple with bound variables
        """
        action = list(action)
        for i, variable in enumerate(action[1:]):
            if not (self.variable_bindings[variable] is None):
                action[i+1] = self.variable_bindings[variable]

        return tuple(action)

    def update_variable_binding(self, dash_result):
        """
        Updates the variable binding map
        :param dash_result: tuple with first element action name, and following
            elements the bound variables
        :return: None
        """

        for i, variable in enumerate(self.action_name_to_variable_map.get(
                                     dash_result[0], [])):
            self.variable_bindings[variable] = dash_result[i+1]


class Index(object):
    """
    Implements a wrapper around an integer to allow a mutable int-like object
    """
    def __init__(self, pos=0):
        self.pos = pos

    def increment(self):
        self.pos += 1

    def decrement(self):
        self.pos -= 1

    def __repr__(self):
        return self.pos.__repr__()

    def __str__(self):
        return self.pos.__str__()
