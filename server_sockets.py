from CONSTANTS import *
import threading

'''
    We provide an exmaple ServerSocket here.
    It is a subclass of threading.Thread, that is,
    it is a threading class.
    You can implement different server sockets with 
    different data analyze methods. Or you use this
    example ServerSocket as the only sockect then
    you need to deal with different type of messages
    in one class.

    We also provide a Meeting class which is used to
    record the meeting information.
    We do not provide any information about the Meeting class,
    so you can design it as you like.
'''

class Meeting():
    def __init__(self):
        pass

class ServerSocket(threading.Thread):
    def __init__(self,conn,addr):
        super(ServerSocket,self).__init__()
        # The connection to send data
        self.conn = conn
        # The address of the client
        self.addr = addr
        # Protocol related - Header
        # If they are with the same format, you can use
        # self.header_format = None
        # self.header_size = 0  
        # Instead
        self.rheader_format = None  # The receiving header format
        self.rheader_size = 0       # The size of the receiving header
        self.sheader_format = None  # The sending header format
        self.sheader_size = 0       # The size of the sending header

    def run(self):
        pass