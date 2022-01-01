import sys; sys.path.extend(['../../'])
from Dash2.core.world_hub import WorldHub
import random


class SimilarityHub(WorldHub):
    # def __init__(self):
    serviceList = {}        # predefined dictionary service_name:service
    serviceDist = {'mail': 0.35, 'social_net':0.85, 'bank':1.0}     # predefined distribution list serv_type:distribution
    knownUsernames = {}     # dictionary service_name:[usernames]

    serviceBase = {}        # dictionary service_name:[(username, password)]
    serviceStatus = {}      # dictionary service_name:[username]

    def processSendActionRequest(self, req_id, action, aux_data):
        print("Processing Action ", action, aux_data)

        if action == 'getAccount':
            service_type = aux_data[0]
            return distPicker(self.serviceDist[service_type], random.random())

        elif action == 'createAccount':
            service = aux_data[0]
            username = aux_data[1]
            password = aux_data[2]
            requirements = self.serviceList[service].getRequirements()
            if username in self.knownUsernames[service]:
                print("Failed: username already exists")
                return('failed:user', [])

            if requirements.verify(username, password):
                print('Success: account successfully created on ', service)
                self.knownUsernames[service].append(username)
                self.serviceBase[service].append((username, password))
                return('success', [])
            else:
                print("Failed: password doesn't meet the requirements")
                return('failed:reqs', [requirements])

        elif action == 'retrieveStatus':
            service = aux_data[0]
            username = aux_data[1]
            if username in self.serviceStatus[service]:
                self.serviceStatus[service].remove(username)
                return ('success', [])
            else:
                return ('failure', [])

if __name__ == "__main__":
    SimilarityHub().run()
