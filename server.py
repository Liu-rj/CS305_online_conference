from CONSTANTS import *
from server_sockets import *
import socket
import threading

'''
    The main server file implements the concurrency via multi-threading.
    You can only modify the total ports and related server socket initiation here.

    If you want to implement the concurrency with other methods,
    you can create a new file to replace this file.
'''

def socket_listen(port):
    '''
        Start a threading function to listen a port
    '''
    # Create a socket
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the address
    sock.bind(('',port))
    # Socket listen
    sock.listen(2)
    # Start to listen
    while True:
        # Wait to client to connect
        conn,address = sock.accept()
        '''
            Modify here
        '''
        # Start the server socket threading class
        if port == XXPORT:
            # Initiate the Port1Socket and start
            # Port1Socket(conn,address).start()
            pass
        elif port == YYPORT:
            # Initiate the Port2Socket and start
            # Port2Socket(conn,address).start()
            pass

if __name__ == "__main__":
    # Threading lists
    ths = []
    
    # Ports which need to listen
    '''Modify here'''
    ports = [XXPORT,YYPORT]

    # Add threadings
    for port in ports:
        ths.append(threading.Thread(target=socket_listen,args=(port,)))
    # Start threading
    try:
        for th in ths:
            th.start()
    except Exception as e:
        print(e)