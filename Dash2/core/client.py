import socket
import struct
import pickle
from Dash2.core.communication_aux import message_types


class Client(object):
    """
    Template class for the client agent
    """
    shared_socket = None

    def __init__(self, host=None, port=None):
        """ Initialization of the client.
        It is required to run Client.run() in order to recieve ID from the
        World Hub.
        Args:
            host(string) - default='localhost' #  hostname of the worldhub
            port(int) - default:5678           # port for opening connections
        Example:
            c = Client()
        """
        self.trace_client = True
        #print("initializing client...")
        if host is None:
            self.server_host = 'localhost'
        else:
            self.server_host = host
        if port is None:
            self.server_port = 5678
        else:
            self.server_port = port
        self.sock = None
        self.id = None
        self.connected = False
        self.traceAction = False

        self.useInternalHub = False  # If true the hub is an object in the same image and sendAction is a function call
        self.hub = None  # the hub if useInternalHub is True

        self.isSharedSocketEnabled = False  # The first agent to use the socket, gets to set up the connection.
        # All other agents with isSharedSocketEnabled = True will reuse it.

    def test(self):
        """
        Registration of the client
        Client establishes connection, and registers the client with the World
        Hub.
        Example:
            c.run()
        """
        try:
            self.register([])
            k = 0

            # test loop
            while k < 100:
                k += 1
                if k % 3 == 0:
                    self.sendAction("look down", [])
                elif k % 2 == 0:
                    self.sendAction("look up", [])
                else:
                    self.getUpdates([])

            print("closing socket...")
            self.disconnect([])
            print("exiting")
            return

        except:
            print("closing socket...")
            self.sock.close()
            print("exiting")

    def establishConnection(self):
        """ Establishes physical connection with the worldhub
        """
        if self.trace_client:
            print("connecting to %s on port %s..." % (self.server_host, self.server_port))

        try:
            if self.isSharedSocketEnabled:
                if Client.shared_socket is None:
                    Client.shared_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    Client.shared_socket.connect((self.server_host, self.server_port))
                self.sock = Client.shared_socket
                # not need to establish connection, because it is assumed that if shared socket is not None,
                # it is already connected to a server.
            else:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_host, self.server_port))
            self.connected = True
            if self.trace_client:
                print("successfully connected.")
        except:
            self.connected = False
            if self.trace_client:  # Maybe should print(this anyway
                print("Problem connecting to hub server, continuing without agent communications")

    def register(self, aux_data=[]):
        """ Register with world hub. Essentially, this is used to assign the client a unique id
        Args:
            aux_data(list) # any extra information you want to relay to the world hub during registration
        """

        if self.useInternalHub:
            if len(aux_data) != 0:
                response = self.hub.processRegisterRequest(self.id, aux_data)
            else:
                response = [self.hub, self.id, None]
        else:
            try:
                if self.trace_client:
                    print("establishing connection...")
            except AttributeError as ae:
                print('It looks as though there was an attempt to register an agent without first calling the base class constructor:')
                print(ae)

            self.establishConnection()

            if not self.connected:
                print("no connection established, agent not registered")
                return None

            if self.trace_client:
                print("registering...")

            response = self.sendAndReceive(message_types['register'], [aux_data])

        result = response[0]
        self.id = response[1]
        aux_response = response[2]

        if self.trace_client:
            print("result: %s." % result)
            print("my id: %d." % self.id)
            print("aux response: %s." % aux_response)

        return response

    def sendAction(self, action, data=[], time="asap"):
        """ Send action in form of message_types['send_action'] to the World Hub
        And awaits the appropriate response
        Args:
            action(string)  #  action to be sent to World Hub
            data(list) #  auxiliary data about the client
            time("asap" or int) #  time to perform action
        Example:
            #to be added
        """

        if self.useInternalHub and self.hub:
            # todo: Currently losing scheduling info - will need to check against timed_hub
            response = self.hub.processSendActionRequest(self.id, action, data)
        elif self.sock is None or not self.connected:
            print('Client sent an action, but there is no connection to a hub. Check if register() was called.')
            return None
        else:
            response = self.sendAndReceive(message_types['send_action'], [self.id, action, data, time])

        # Allow for the result to be a list, e.g. ['success', [data]], or just an object, e.g. 'fail'.
        # However if the return object is a list it must have the first form.
        if isinstance(response, (list, tuple)):
            if len(response) == 0:
                print('empty response from server for action', action, data, time)
                return response
            result = response[0]
            if len(response) > 1:
                aux_response = response[1]
            else:
                aux_response = []
        else:
            result = response
            aux_response = []

        if self.traceAction:
            print("hub action", action, str(data) if data else "", \
                "received response:", result, ", aux response: " + str(aux_response) if aux_response != [] else "")

        self.processActionResponse(result, aux_response)

        return response

    def getUpdates(self, aux_data=[]):
        """ Sends request for update with the aux_data and receives the update
        from the World Hub
        Args:
            aux_data(list)    # Data to be sent to the world hub
        Example:
            #to be added
        """
        if self.useInternalHub:
            response = self.hub.processGetUpdatesRequest(self.id, aux_data)
        else:
            response = self.sendAndReceive(message_types['get_updates'], [self.id, aux_data])
        aux_response = response[0]

        if self.trace_client:
            print("successfully received response...")
            print("aux data: %s." % aux_data)

        self.processUpdates(aux_response)

        return

    def disconnect(self, aux_data=[]):
        """ Sends request to disconnect from world hub"
        Args:
            aux_data(list)    # Data to be sent to the world hub
        """
        if self.useInternalHub:
            return

        if self.sock is not None and self.isSharedSocketEnabled is False:
            if self.connected:
                self.sendMessage(message_types['disconnect'], [self.id, aux_data])
                self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

        if self.sock is not None and self.isSharedSocketEnabled is True:
            if self.connected and self.shared_socket :
                try:
                    self.sendMessage(message_types['disconnect'], [self.id, aux_data])
                    self.sock.shutdown(socket.SHUT_RDWR)
                except socket.error as err:
                    if self.trace_client:
                        print("already closed")

        if self.trace_client:
            print("disconnecting from world hub" + "." if self.connected else ", no message sent since already not connected.")


        #sys.exit(0)  # Should not automatically kill the process

    def processActionResponse(self, result, aux_response):
        # we may want to hook in some sort of inference engine here
        self.processUpdates(aux_response)
        return

    def processUpdates(self, aux_data):
        return

    def sendAndReceive(self, message_type, message_contents):
        self.sendMessage(message_type, message_contents)
        return self.receiveResponse()

    def sendMessage(self, message_type, message_contents):
        # send message header followed by serialized contents
        serialized_message_contents = pickle.dumps(message_contents)
        message_len = len(serialized_message_contents)
        message_header = struct.pack("!II", message_type, message_len)
        message = message_header + serialized_message_contents
        return self.sock.sendall(message)

    def receiveResponse(self):
        # read header (i.e., find length of response)
        bytes_read = 0
        bytes_to_read = 4
        response_header = "".encode()
        while bytes_read < bytes_to_read:
            data = self.sock.recv(bytes_to_read - bytes_read)
            if data:
                response_header += data
                bytes_read += len(data)
            else:
                print("trouble receiving message...")
                self.sock.close()
        response_len, = struct.unpack("!I", response_header)

        # read message
        bytes_read = 0
        bytes_to_read = response_len
        serialized_response = "".encode()
        while bytes_read < bytes_to_read:
            data = self.sock.recv(bytes_to_read - bytes_read)
            if data:
                serialized_response += data
                bytes_read += len(data)
            else:
                self.sock.close()
        response = pickle.loads(serialized_response)

        return response

if __name__ == "__main__":
    """ Simplistic command line driver
    """
    c = Client()
    c.test()
