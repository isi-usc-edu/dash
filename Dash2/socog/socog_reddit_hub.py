from Dash2.core.world_hub import WorldHub


class Reddit(WorldHub):
    """
    Test class for socog module
    """
    def __init__(self, **kwargs):
        WorldHub.__init__(self, kwargs.get('port', None))
        self.users = set()
        self.comments = self._initialize_comments()

    def _initialize_comments(self):
        """
        Create some initial comments. A simulated Soccer forum where people like
        the player Henry who is on the GreyTeam. They find out that Henry
        cheated and then people start negative comments about Henry and the
        GreyTeam as they adjust their beliefs.
        :return: list of strings
        """

        return [
            'GreyTeam is Best',
            'Henry is Corrupt',
            'Henry is Best',
            'Henry is Corrupt',
            'Henry is not Best',
            'GreyTeam is not Best',
            'Henry is Corrupt',
            'Soccer is Corrupt',
            'Soccer is not Best',
            'GreyTeam is Corrupt'
        ]
        # return [
        #     'Soccer is not Corrupt',
        #     'GreyTeam is with Soccer',
        #     'GreyTeam is Best',
        #     'GreyTeam is Corrupt',
        #     'Henry is with GreyTeam',
        #     'Henry is Best',
        #     'Corrupt is not Best',
        #     'Soccer is not Corrupt',
        #     'Henry is Corrupt',
        #     'Soccer is not Corrupt',
        #     'GreyTeam is Best',
        #     'Henry is Corrupt',
        #     'GreyTeam is Corrupt',
        #     'Soccer is Best',
        #     'Henry is not Best',
        #     'GreyTeam is not Best'
        # ]

    def processRegisterRequest(self, agent_id, aux_data):
        self.users.add(agent_id)
        return ["success", agent_id, []]

    def read_comment(self, agent_id, args):
        index = args[0]
        if len(self.comments) > index:
            return ['success', self.comments[index]]
        else:
            return ['failure', []]

    def write_comment(self, agent_id, args):
        comment = args[0]
        self.comments.append(comment)
        print(agent_id, 'added comment...', comment)
        print('current thread:')
        print(self.comments)
        return ['success', len(self.comments)-1]


if __name__ == "__main__":
    Reddit(port=6002).run()
