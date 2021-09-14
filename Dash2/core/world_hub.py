#!/usr/bin/env python
# this is adapted from http://ilab.cs.byu.edu/python/threadingmodule.html
import sys
sys.path.extend(['../../']) # need to have 'webdash' directory in $PYTHONPATH, if we want to run script (as "__main__")
import select
import socket
import threading
import struct
import pickle
import re
import traceback
from Dash2.core.communication_aux import message_types


class WorldHub:

    lowest_unassigned_id = 0
    lock = threading.Lock()

    ############################################################
    # you should only need to modify a few world hub functions #
    #                                                          #
    # usually you'll only need to modify:                      #
    #  - processRegisterRequest                                # 
    #  - processGetUpdatesRequest                              #
    #  - processSendActionRequest                              #
    #  - updateState                                           #
    #  - getUpdates                                            #
    #                                                          #
    # you might also modify:                                   #
    #  - processDisconnectRequest                              #
    #                                                          #
    # remember to acquire lock for critical regions!           #
    ############################################################

    def processRegisterRequest(self, id, aux_data):
        aux_response = []
        return ["success", id, aux_response]

    def processGetUpdatesRequest(self, id, aux_data):
        aux_response = self.getUpdates(id, aux_data)
        return [aux_response]

    # The default processSendActionRequest looks at the name of the action and tries to map it to a method
    # on the hub object, either with the same name or with a name that has camel case turned to underscores,
    # e.g. "LogMeIn" -> log_me_in. The method is called with the agent_id and the data
    def processSendActionRequest(self, agent_id, action, data):
        if hasattr(self, action) and callable(getattr(self, action)):
            return getattr(self, action)(agent_id, data)
        underscore_action = convert_camel(action)
        if hasattr(self, underscore_action) and callable(getattr(self, underscore_action)):
            return getattr(self, underscore_action)(agent_id, data)
        # fallthrough code
        print('Calling base class processSendActionRequest since neither', action, 
              "nor", underscore_action, "were found as methods")
        aux_response = self.updateState(agent_id, action, data) + self.getUpdates(agent_id, data)
        return ['success', aux_response]

    def processDisconnectRequest(self, id, aux_data):
        print("Client {} has disconnected from the world hub.".format(id))
        return "this is ignored"

    def updateState(self, id, action, aux_data):
        return []

    def getUpdates(self, id, aux_data):
        return []

    ####################################################################
    # you probably shouldn't need to modify anything after this point! #
    ####################################################################

    def __init__(self, port=None):
        print("initializing world hub...")
        self.host = 'localhost'
        if port is None:
            self.port = 5678
        else:
            self.port = port
        self.backlog = 5
        self.server = None
        self.threads = []
        self.trace_handler = True
        self.save_request_history = False
        self.request_history = True

    def run(self):
        # attempt to open a socket with initialized values.
        print("opening socket...")
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.host, self.port))
            self.server.listen(self.backlog)
        except socket.error as err:
            if self.server:
                self.server.close()
            print("could not open. socket. following error occurred: {}".format(err))
            sys.exit(1)
        
        # listen for new connections.
        print("successfully opened socket. listening for new connections...")
        print("if you wish to quit the server program, enter q")
        input = [self.server, sys.stdin]
        self.listening = True  # An instance variable so that we can break this loop from outside if necessary
        while self.listening:
            input_ready, output_ready, except_ready = select.select(input, [], [])
            for s in input_ready:
                # if a new connection is requested, start a new thread for it
                if s == self.server:
                    c = self.createServeClientThread(self.server.accept())
                    c.trace_handler = self.trace_handler
                    c.start()
                    self.threads.append(c)
                # else if we got input from the keyboard, stop
                elif s == sys.stdin:
                    user_input = \
                        sys.stdin.readline()
                    if user_input == "q\n":
                        self.listening = False
                    else:
                        print("if you wish to quit, enter q.")
        
        # quit
        print("quitting program as requested by user...")
        self.server.close()
        for c in self.threads:
            c.join()
        self.terminateWork()


    # This method is intended to be overridden by subclasses to point to a ServeClientThread subclass
    def createServeClientThread(self, client_address_tuple):
        return ServeClientThread(self, client_address_tuple)


    # This method is intended to operations need before termination of the hub. For example, releaseing OS resources,
    # handling persistance, dumping cansh into files, etc.
    def terminateWork(self):
        pass

class ServeClientThread(threading.Thread):

    def __init__(self, hub, client_address_tuple):
        threading.Thread.__init__(self)
        self.client = client_address_tuple[0]
        self.address = client_address_tuple[1]
        self.size = 1024
        self.hub = hub
        self.trace_handler = True
        self.running = False

        return

    def run(self):

        try:
            self.running = True
            while self.running:
                # determine what the client wants
                [message_type, message] = self.getClientRequest()

                if self.trace_handler:
                    print("received following information in client request:")
                    print("message type: %s" % message_type)
                    print("message: %s" % message)
                
                # do something with the message....
                # types of messages to consider: register id, process action, update state 
                self.handleClientRequest(message_type, message)

            print('Client disconnected')

        except BaseException as e:
            print("closing socket...", e)
            traceback.print_exc()
            self.client.close()
            print("exiting client thread")

    # read message and return a list of form [client_id, message_type, message_contents]
    def getClientRequest(self):
        # read first 4 bytes for message len
        if self.trace_handler:
            print("getting message type and message length...")
        bytes_read = 0
        bytes_expected = 8
        message_header = b''
        while bytes_read < bytes_expected:
            data = self.client.recv(bytes_expected - bytes_read)
            if data:
                message_header += data
                bytes_read += len(data)
            else:
                self.client.close()
                running = 0
        message_type, message_len = struct.unpack("!II", message_header)

        if self.trace_handler:
            print("message type: %d" % message_type)
            print("message len: %d" % message_len)

        # read payload
        if self.trace_handler:
            print("getting payload...")
        bytes_read = 0
        bytes_expected = message_len
        message = "".encode()
        while bytes_read < bytes_expected:
            data = self.client.recv(bytes_expected - bytes_read)
            if data:
                message += data
                bytes_read += len(data)
            else:
                self.client.close()
        message_payload = pickle.loads(message)

        if self.trace_handler:
            print("successfully retrieved payload %s ... returning." % message_payload)

        return [message_type, message_payload]

    def handleClientRequest(self, message_type, message_payload):
        # 3 types:
        #    0: register id, update state
        #    1: handle action, update state, relay relevant observations to client
        #    2: relay recent observations to client
        if message_types['register'] == message_type:
            response = self.handleRegisterRequest(message_payload)
        elif message_types['send_action'] == message_type:
            response = self.handleSendActionRequest(message_payload)
        elif message_types['get_updates'] == message_type:
            response = self.handleGetUpdatesRequest(message_payload)
        elif message_types['disconnect'] == message_type:
            self.handleDisconnectRequest(message_payload)
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                pass
            self.client.close()
            #sys.exit(0)  # don't necessarily want to exit the hub when one agent disconnects
            self.running = False  # This will end the listen loop in the 'run' method
        else:
            print("uhoh!")

        if self.running:
            self.sendMessage(response)

        return

    def sendMessage(self, unserialized_message):
        serialized_message = pickle.dumps(unserialized_message)
        message_len = len(serialized_message)
        message = struct.pack("!I", message_len) + serialized_message
        self.client.sendall(message)
        
        return
    
    def handleRegisterRequest(self, message):
        if self.trace_handler:
            print('handling registration request...')
        aux_data = message[0]
        return self.processRegisterRequestWrapper(aux_data)

    def handleSendActionRequest(self, message):
        if self.trace_handler:
            print('handling send action request for', self, '...')
        id = message[0]
        action = message[1]
        aux_data = message[2]
        return self.processSendActionRequest(id, action, aux_data)

    def handleGetUpdatesRequest(self, message):
        if self.trace_handler:
            print('handling get updates request...')
        id = message[0]
        aux_data = message[1]
        return self.processGetUpdatesRequest(id, aux_data)

    def handleDisconnectRequest(self, message):
        if self.trace_handler:
            print('handling disconnect request...')
        id = message[0]
        aux_data = message[1]
        return self.processDisconnectRequest(id, aux_data)

    def processRegisterRequestWrapper(self, aux_data):
        with self.hub.lock:
            assigned_id = self.hub.lowest_unassigned_id
            self.hub.lowest_unassigned_id += 1
        return self.processRegisterRequest(assigned_id, aux_data)

    ######################################################################
    # the following functions are wrappers that call world hub functions #
    #                                                                    #
    # you probably shouldn't need to modify them                         #
    ######################################################################

    def processRegisterRequest(self, id, aux_data):
        return self.hub.processRegisterRequest(id, aux_data)

    def processGetUpdatesRequest(self, id, aux_data):
        return self.hub.processGetUpdatesRequest(id, aux_data)
            
    def processSendActionRequest(self, id, action, aux_data):
        return self.hub.processSendActionRequest(id, action, aux_data)

    def processDisconnectRequest(self, id, aux_data):
        return self.hub.processDisconnectRequest(id, aux_data)

    # I don't know why this was here...
    # Are there instances where we'd want the client to simply change 
    # world state without performing an action?
    # And if so, why not just send action = None or something instead?
#    def updateState(self, id, action, aux_data):
#        return self.hub.updateState(id, action, aux_data)

    def getUpdates(self, id, aux_data):
        return self.hub.getUpdates(id, aux_data)


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


# Convert CamelCase to camel_case etc.
def convert_camel(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


if __name__ == "__main__":
    s = WorldHub()
    s.run()
