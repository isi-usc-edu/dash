# the client and server communicate via a simple messaging
# protocol as briefly explained in this file
#
# "message_type, length, message_contents"
#
# where length is the length of the complete message
#       message_type is 4 a byte integer that specify the kind of message
#       length is a 4 byte integer that specifies the length of the message payload
#       message_contents is the message payload
#
# length and message_type can be though of as the header
# and message_contents can be thought of the payload
# 
# The basic messages are as follows.
#
# register:
# "0, length, [aux_information]" (sent from client to server)
# "length, [result, client_id, aux_information]" (sent from server to client)
# 
#
# perform_action:
# "1, length, [client_id, action, aux_information]" (sent from client to server)
# "length, [result, updates/aux_information]" (sent from server to client)
#
# update_state:
# "2, length, [client_id, aux_information]" (sent from client to server)
# "length, [updates/aux_informatiion]" (sent from server to client)
import struct
import socket
import pickle

message_types = {
    'register':    0,
    'send_action': 1,
    'get_updates': 2,
    'disconnect': 3
    }
