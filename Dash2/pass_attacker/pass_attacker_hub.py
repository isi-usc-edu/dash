import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub


class ServiceHub(WorldHub):
    # def __init__(self):
    serviceList = {}    # predefined dictionary service_name:service
    serviceDist = {'mail': 0.35, 'social_net':0.85, 'bank':1.0}    # predefined distribution list serv_type:distribution
    knownUsernames = {}    # dictionary service_name:[usernames]

    serviceBase = {}    # dictionary service_name:[(username, password)]
    serviceStatus = {}    # dictionary service_name:[username]

    def processSendActionRequest(self, id, action, aux_data):
        print(("Processing Action ", action, aux_data))

        print(action)
        if action == 'directAttack':
            # service_type = aux_data[0]
            return ['success', 'bank1']
            #return ['success', distPicker(self.serviceDist[service_type], random.random())]

        elif action == 'indirectAttack':
            return ['success', 'bank1']

        elif action == 'findUncompromisedSite':
            return ['success', 'bank1']

        elif action == 'findCompromisedSite':
            return ['success', 'bank1']

        elif action == 'reusePassword':
            return ['success', 'bank1']


if __name__ == "__main__":
    ServiceHub().run()
